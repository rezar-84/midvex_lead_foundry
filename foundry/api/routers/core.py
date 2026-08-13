from __future__ import annotations

from datetime import datetime
from typing import Literal, cast

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from pydantic import Field

from ...access import CAPABILITIES
from ...audit import record_event
from ...models import Company, Conversation, OpportunityCandidate, ReviewDecision
from ...runtime_settings import runtime_setting
from ..pagination import paginate_queryset
from ..security import require_membership

router = Router()


class OrganizationOut(Schema):
    id: str
    name: str
    retention_days: int | None


class FlagsOut(Schema):
    gmail_real_data_enabled: bool
    source_network_enabled: bool
    enrichment_network_enabled: bool


class MeOut(Schema):
    username: str
    role: str
    capabilities: list[str]
    organization: OrganizationOut
    brand_name: str
    flags: FlagsOut


class PageMeta(Schema):
    count: int
    page: int
    pages: int
    per_page: int


class OpportunityOut(Schema):
    id: str
    title: str
    reason: str
    rule_code: str
    status: str
    score: float | None
    confidence: float | None
    last_communication_at: datetime | None
    conversation_subject: str


class EvidenceOut(Schema):
    message_id: str
    subject: str
    snippet: str
    sha256: str


class OpportunityDetailOut(OpportunityOut):
    evidence: EvidenceOut


class OpportunityPageOut(PageMeta):
    items: list[OpportunityOut]


class DashboardOut(Schema):
    pending_count: int
    accepted_count: int
    conversation_count: int
    recent: list[OpportunityOut]


class ReviewIn(Schema):
    decision: Literal["accepted", "rejected", "deferred"]
    note: str = Field(default="", max_length=2000)


class ConversationOut(Schema):
    id: str
    subject: str
    last_message_at: datetime | None


class ConversationPageOut(PageMeta):
    items: list[ConversationOut]


class ContactOut(Schema):
    id: str
    display_name: str
    primary_email: str
    phone: str


class CompanyOut(Schema):
    id: str
    name: str
    domain: str
    website: str
    contacts: list[ContactOut]


class CompanyPageOut(PageMeta):
    items: list[CompanyOut]


def _opportunity_out(candidate: OpportunityCandidate) -> OpportunityOut:
    return OpportunityOut(
        id=str(candidate.id),
        title=candidate.title,
        reason=candidate.reason,
        rule_code=candidate.rule_code,
        status=candidate.status,
        score=float(candidate.score) if candidate.score is not None else None,
        confidence=float(candidate.confidence) if candidate.confidence is not None else None,
        last_communication_at=candidate.last_communication_at,
        conversation_subject=candidate.conversation.subject,
    )


@router.get("/me", response=MeOut, url_name="me")
def me(request: HttpRequest) -> MeOut:
    membership = require_membership(request, "view")
    organization = membership.organization
    return MeOut(
        username=membership.user.get_username(),
        role=membership.role,
        capabilities=sorted(CAPABILITIES.get(membership.role, frozenset())),
        organization=OrganizationOut(
            id=str(organization.id),
            name=organization.name,
            retention_days=organization.retention_days,
        ),
        brand_name=runtime_setting("FOUNDRY_BRAND_NAME"),
        flags=FlagsOut(
            gmail_real_data_enabled=bool(settings.GMAIL_REAL_DATA_ENABLED),
            source_network_enabled=bool(settings.SOURCE_NETWORK_ENABLED),
            enrichment_network_enabled=bool(settings.ENRICHMENT_NETWORK_ENABLED),
        ),
    )


@router.get("/dashboard", response=DashboardOut, url_name="dashboard")
def dashboard(request: HttpRequest) -> DashboardOut:
    membership = require_membership(request, "view")
    candidates = OpportunityCandidate.objects.filter(organization=membership.organization)
    return DashboardOut(
        pending_count=candidates.filter(status=OpportunityCandidate.Status.PENDING).count(),
        accepted_count=candidates.filter(status=OpportunityCandidate.Status.ACCEPTED).count(),
        conversation_count=Conversation.objects.filter(
            organization=membership.organization
        ).count(),
        recent=[
            _opportunity_out(candidate)
            for candidate in candidates.select_related("conversation").order_by("-created_at")[:8]
        ],
    )


@router.get("/opportunities", response=OpportunityPageOut, url_name="opportunities")
def opportunities(
    request: HttpRequest, status: str = OpportunityCandidate.Status.PENDING, page: int = 1
) -> OpportunityPageOut:
    membership = require_membership(request, "view")
    valid = {choice for choice, _ in OpportunityCandidate.Status.choices}
    items = OpportunityCandidate.objects.filter(organization=membership.organization)
    if status in valid:
        items = items.filter(status=status)
    objects, meta = paginate_queryset(
        items.select_related("conversation").order_by("-score"), page, per_page=25
    )
    return OpportunityPageOut(items=[_opportunity_out(candidate) for candidate in objects], **meta)


@router.get(
    "/opportunities/{candidate_id}", response=OpportunityDetailOut, url_name="opportunity_detail"
)
def opportunity_detail(request: HttpRequest, candidate_id: str) -> OpportunityDetailOut:
    membership = require_membership(request, "view")
    candidate = get_object_or_404(
        OpportunityCandidate.objects.select_related("conversation", "evidence_message"),
        organization=membership.organization,
        id=candidate_id,
    )
    base = _opportunity_out(candidate)
    return OpportunityDetailOut(
        **base.model_dump(),
        evidence=EvidenceOut(
            message_id=str(candidate.evidence_message.id),
            subject=candidate.evidence_message.subject,
            snippet=candidate.evidence_message.snippet,
            sha256=candidate.evidence_message.raw_sha256,
        ),
    )


@router.post(
    "/opportunities/{candidate_id}/review",
    response=OpportunityDetailOut,
    url_name="review_opportunity",
)
def review_opportunity(
    request: HttpRequest, candidate_id: str, payload: ReviewIn
) -> OpportunityDetailOut:
    membership = require_membership(request, "review")
    with transaction.atomic():
        candidate = get_object_or_404(
            OpportunityCandidate.objects.select_for_update(),
            organization=membership.organization,
            id=candidate_id,
        )
        candidate.status = payload.decision
        candidate.save(update_fields=["status", "updated_at"])
        ReviewDecision.objects.create(
            organization=membership.organization,
            candidate=candidate,
            reviewer=cast(User, request.user),
            decision=candidate.status,
            note=payload.note,
        )
        record_event(
            request,
            membership.organization,
            "opportunity.reviewed",
            object_type="opportunity",
            object_id=str(candidate.id),
            metadata={"decision": candidate.status},
        )
    return opportunity_detail(request, candidate_id)


@router.get("/conversations", response=ConversationPageOut, url_name="conversations")
def conversations(request: HttpRequest, page: int = 1) -> ConversationPageOut:
    membership = require_membership(request, "view")
    items = Conversation.objects.filter(organization=membership.organization).order_by(
        "-last_message_at"
    )
    objects, meta = paginate_queryset(items, page, per_page=50)
    return ConversationPageOut(
        items=[
            ConversationOut(
                id=str(conversation.id),
                subject=conversation.subject,
                last_message_at=conversation.last_message_at,
            )
            for conversation in objects
        ],
        **meta,
    )


@router.get("/knowledge", response=CompanyPageOut, url_name="knowledge")
def knowledge(request: HttpRequest, page: int = 1) -> CompanyPageOut:
    membership = require_membership(request, "view")
    companies = (
        Company.objects.filter(organization=membership.organization)
        .prefetch_related("contacts")
        .order_by("name")
    )
    objects, meta = paginate_queryset(companies, page, per_page=24)
    return CompanyPageOut(
        items=[
            CompanyOut(
                id=str(company.id),
                name=company.name,
                domain=company.domain,
                website=company.website,
                contacts=[
                    ContactOut(
                        id=str(contact.id),
                        display_name=contact.display_name,
                        primary_email=contact.primary_email,
                        phone=contact.phone,
                    )
                    for contact in company.contacts.all()
                ],
            )
            for company in objects
        ],
        **meta,
    )
