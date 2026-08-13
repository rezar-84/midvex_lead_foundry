from __future__ import annotations

from datetime import datetime
from typing import Literal, cast

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from ...access import CAPABILITIES
from ...audit import record_event
from ...models import (
    Company,
    Conversation,
    MailboxConnection,
    OpportunityCandidate,
    ReviewDecision,
)
from ...runtime_settings import EDITABLE_KEYS, runtime_setting, set_runtime_setting
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


# --- org sources & instance settings ----------------------------------------


class MailboxOut(Schema):
    id: str
    provider: str
    email_address: str
    status: str
    scopes: list[str]
    policy_confirmed_at: datetime | None
    created_at: datetime


class SettingRowOut(Schema):
    label: str
    value: str
    key: str
    editable: bool
    secret: bool


class SettingGroupOut(Schema):
    title: str
    rows: list[SettingRowOut]


class SettingUpdateIn(Schema):
    value: str = ""


def _mask(value: str) -> str:
    if not value:
        return ""
    return f"{value[:4]}…{value[-2:]}" if len(value) > 8 else "set"


@router.get("/sources", response=list[MailboxOut], url_name="sources")
def sources(request: HttpRequest) -> list[MailboxOut]:
    membership = require_membership(request, "manage_sources")
    mailboxes = MailboxConnection.objects.filter(organization=membership.organization).order_by(
        "email_address"
    )
    return [
        MailboxOut(
            id=str(mailbox.id),
            provider=mailbox.provider,
            email_address=mailbox.email_address,
            status=mailbox.status,
            scopes=[str(scope) for scope in mailbox.scopes],
            policy_confirmed_at=mailbox.policy_confirmed_at,
            created_at=mailbox.created_at,
        )
        for mailbox in mailboxes
    ]


@router.get("/instance-settings", response=list[SettingGroupOut], url_name="instance_settings")
def instance_settings(request: HttpRequest) -> list[SettingGroupOut]:
    require_membership(request, "manage_users")
    raw_groups: list[tuple[str, list[tuple[str, str, str]]]] = [
        (
            "Branding & locale",
            [
                ("Brand name", runtime_setting("FOUNDRY_BRAND_NAME"), "FOUNDRY_BRAND_NAME"),
                (
                    "Enrichment user-agent",
                    runtime_setting("FOUNDRY_USER_AGENT"),
                    "FOUNDRY_USER_AGENT",
                ),
                ("Language code", settings.LANGUAGE_CODE, "DJANGO_LANGUAGE_CODE"),
                (
                    "Languages",
                    ", ".join(code for code, _ in settings.LANGUAGES),
                    "DJANGO_LANGUAGES",
                ),
                ("Time zone", settings.TIME_ZONE, "DJANGO_TIME_ZONE"),
            ],
        ),
        (
            "Google OAuth (Gmail read-only)",
            [
                ("Client ID", _mask(runtime_setting("GOOGLE_CLIENT_ID")), "GOOGLE_CLIENT_ID"),
                (
                    "Client secret",
                    "set" if runtime_setting("GOOGLE_CLIENT_SECRET") else "",
                    "GOOGLE_CLIENT_SECRET",
                ),
                ("Redirect URI", runtime_setting("GOOGLE_REDIRECT_URI"), "GOOGLE_REDIRECT_URI"),
            ],
        ),
        (
            "Policy gates (human approval required to enable)",
            [
                (
                    "Real Gmail data",
                    "enabled" if settings.GMAIL_REAL_DATA_ENABLED else "disabled",
                    "GMAIL_REAL_DATA_ENABLED",
                ),
                (
                    "External source sync",
                    "enabled" if settings.SOURCE_NETWORK_ENABLED else "disabled",
                    "SOURCE_NETWORK_ENABLED",
                ),
                (
                    "Enrichment network",
                    "enabled" if settings.ENRICHMENT_NETWORK_ENABLED else "disabled",
                    "ENRICHMENT_NETWORK_ENABLED",
                ),
                (
                    "Enrichment egress proxy",
                    "set" if runtime_setting("ENRICHMENT_EGRESS_PROXY") else "",
                    "ENRICHMENT_EGRESS_PROXY",
                ),
            ],
        ),
        (
            "Storage & limits",
            [
                ("Evidence backend", settings.RAW_STORAGE_BACKEND, "RAW_STORAGE_BACKEND"),
                ("S3 bucket", settings.S3_BUCKET or "", "S3_BUCKET"),
                ("S3 endpoint", settings.S3_ENDPOINT_URL or "", "S3_ENDPOINT_URL"),
                (
                    "Max message size",
                    f"{settings.MAX_MESSAGE_BYTES // (1024 * 1024)} MB",
                    "MAX_MESSAGE_BYTES",
                ),
                (
                    "Token encryption key",
                    "set" if settings.TOKEN_ENCRYPTION_KEY else "derived (dev only)",
                    "TOKEN_ENCRYPTION_KEY",
                ),
            ],
        ),
    ]
    return [
        SettingGroupOut(
            title=title,
            rows=[
                SettingRowOut(
                    label=label,
                    value=value,
                    key=key,
                    editable=key in EDITABLE_KEYS,
                    secret=EDITABLE_KEYS[key].secret if key in EDITABLE_KEYS else False,
                )
                for label, value, key in rows
            ],
        )
        for title, rows in raw_groups
    ]


@router.put("/instance-settings/{key}", response=dict[str, str], url_name="instance_setting_update")
def instance_setting_update(
    request: HttpRequest, key: str, payload: SettingUpdateIn
) -> dict[str, str]:
    membership = require_membership(request, "manage_users")
    if key not in EDITABLE_KEYS:
        raise HttpError(404, "That setting is not editable from the interface.")
    value = payload.value.strip()
    set_runtime_setting(key, value)
    record_event(
        request,
        membership.organization,
        "instance_setting.updated",
        object_type="instance_setting",
        object_id=key,
        metadata={"cleared": not value},
    )
    return {"key": key, "state": "cleared" if not value else "updated"}
