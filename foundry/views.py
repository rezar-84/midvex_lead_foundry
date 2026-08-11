from __future__ import annotations

import secrets
from typing import cast

import pyotp
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .access import require_capability
from .audit import record_event
from .crypto import decrypt, encrypt
from .exports import accepted_candidates_csv
from .forms import MFAForm, ReviewDecisionForm, SourceConnectForm
from .gmail import READONLY_SCOPE, oauth_flow
from .models import (
    Company,
    Conversation,
    LeadSource,
    MailboxConnection,
    MFADevice,
    OpportunityCandidate,
    ReviewDecision,
)


def health(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok", content_type="text/plain")


@login_required
@require_http_methods(["GET", "POST"])
def mfa_setup(request: HttpRequest) -> HttpResponse:
    device, _ = MFADevice.objects.get_or_create(
        user=request.user, defaults={"encrypted_secret": encrypt(pyotp.random_base32())}
    )
    if device.confirmed_at:
        return redirect("mfa_verify")
    secret = decrypt(device.encrypted_secret)
    form = MFAForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        totp = pyotp.TOTP(secret)
        if totp.verify(form.cleaned_data["code"], valid_window=1):
            device.confirmed_at = timezone.now()
            device.last_counter = totp.timecode(timezone.now())
            device.save(update_fields=["confirmed_at", "last_counter", "updated_at"])
            request.session["mfa_verified"] = True
            return redirect("dashboard")
        form.add_error("code", "Invalid authentication code.")
    uri = pyotp.TOTP(secret).provisioning_uri(
        name=request.user.get_username(), issuer_name="Midvex Lead Foundry"
    )
    return render(
        request, "foundry/mfa_setup.html", {"form": form, "secret": secret, "provisioning_uri": uri}
    )


@login_required
@require_http_methods(["GET", "POST"])
def mfa_verify(request: HttpRequest) -> HttpResponse:
    device = get_object_or_404(MFADevice, user=request.user, confirmed_at__isnull=False)
    form = MFAForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        totp = pyotp.TOTP(decrypt(device.encrypted_secret))
        counter = totp.timecode(timezone.now())
        if counter > device.last_counter and totp.verify(form.cleaned_data["code"], valid_window=1):
            device.last_counter = counter
            device.save(update_fields=["last_counter", "updated_at"])
            request.session["mfa_verified"] = True
            return redirect("dashboard")
        form.add_error("code", "Invalid or previously used authentication code.")
    return render(request, "foundry/mfa_verify.html", {"form": form})


@login_required
@require_capability("view")
def dashboard(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    candidates = OpportunityCandidate.objects.filter(organization=membership.organization)
    context = {
        "pending_count": candidates.filter(status=OpportunityCandidate.Status.PENDING).count(),
        "accepted_count": candidates.filter(status=OpportunityCandidate.Status.ACCEPTED).count(),
        "conversation_count": Conversation.objects.filter(
            organization=membership.organization
        ).count(),
        "recent": candidates.select_related("conversation").order_by("-created_at")[:8],
    }
    return render(request, "foundry/dashboard.html", context)


@login_required
@require_capability("view")
def conversations(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    items = Conversation.objects.filter(organization=membership.organization).order_by(
        "-last_message_at"
    )
    return render(request, "foundry/conversations.html", {"conversations": items})


@login_required
@require_capability("view")
def knowledge(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    companies = (
        Company.objects.filter(organization=membership.organization)
        .prefetch_related("contacts")
        .order_by("name")
    )
    return render(request, "foundry/knowledge.html", {"companies": companies})


@login_required
@require_capability("view")
def opportunities(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    status = request.GET.get("status", OpportunityCandidate.Status.PENDING)
    valid = {choice for choice, _ in OpportunityCandidate.Status.choices}
    items = OpportunityCandidate.objects.filter(organization=membership.organization)
    if status in valid:
        items = items.filter(status=status)
    return render(
        request,
        "foundry/opportunities.html",
        {"opportunities": items.order_by("-score"), "status": status},
    )


@login_required
@require_capability("view")
def opportunity_detail(request: HttpRequest, candidate_id: str) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    candidate = get_object_or_404(
        OpportunityCandidate.objects.select_related("conversation", "evidence_message"),
        organization=membership.organization,
        id=candidate_id,
    )
    return render(
        request,
        "foundry/opportunity_detail.html",
        {"candidate": candidate, "form": ReviewDecisionForm()},
    )


@login_required
@require_POST
@require_capability("review")
@transaction.atomic
def review_opportunity(request: HttpRequest, candidate_id: str) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    candidate = get_object_or_404(
        OpportunityCandidate.objects.select_for_update(),
        organization=membership.organization,
        id=candidate_id,
    )
    form = ReviewDecisionForm(request.POST)
    if form.is_valid():
        candidate.status = form.cleaned_data["decision"]
        candidate.save(update_fields=["status", "updated_at"])
        ReviewDecision.objects.create(
            organization=membership.organization,
            candidate=candidate,
            reviewer=cast(User, request.user),
            decision=candidate.status,
            note=form.cleaned_data["note"],
        )
        record_event(
            request,
            membership.organization,
            "opportunity.reviewed",
            object_type="opportunity",
            object_id=str(candidate.id),
            metadata={"decision": candidate.status},
        )
        messages.success(request, "Review decision saved.")
    else:
        messages.error(request, "The review decision was not valid.")
    return redirect("opportunity_detail", candidate_id=candidate.id)


@login_required
@require_POST
@require_capability("export")
def export_csv(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    batch, content = accepted_candidates_csv(membership.organization, cast(User, request.user))
    record_event(
        request,
        membership.organization,
        "export.created",
        object_type="export",
        object_id=str(batch.id),
        metadata={"record_count": batch.record_count},
    )
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="accepted-opportunities-{batch.id}.csv"'
    )
    return response


@login_required
@require_capability("manage_sources")
def sources(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    mailboxes = MailboxConnection.objects.filter(organization=membership.organization).order_by(
        "email_address"
    )
    return render(
        request,
        "foundry/sources.html",
        {
            "mailboxes": mailboxes,
            "form": SourceConnectForm(),
            "gmail_enabled": settings.GMAIL_REAL_DATA_ENABLED,
        },
    )


@login_required
@require_POST
@require_capability("manage_sources")
def gmail_connect(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    form = SourceConnectForm(request.POST)
    if not form.is_valid() or not membership.organization.retention_days:
        messages.error(
            request, "Authority confirmation and an organisation retention policy are required."
        )
        return redirect("sources")
    state = secrets.token_urlsafe(32)
    request.session["gmail_oauth_state"] = state
    request.session["gmail_policy_confirmed"] = True
    flow = oauth_flow(state=state)
    url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    return redirect(url)


@login_required
@require_capability("manage_sources")
def gmail_callback(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    state = request.session.pop("gmail_oauth_state", None)
    policy_confirmed = request.session.pop("gmail_policy_confirmed", False)
    lead_source_id = request.session.pop("gmail_lead_source_id", None)
    if not state or not policy_confirmed or request.GET.get("state") != state:
        return HttpResponse("Invalid OAuth state", status=400)
    flow = oauth_flow(state=state)
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials
    if READONLY_SCOPE not in set(credentials.scopes or []):
        return HttpResponse("Required read-only Gmail scope was not granted", status=400)
    if not credentials.refresh_token:
        return HttpResponse("Google did not return an offline refresh token", status=400)
    service = __import__("googleapiclient.discovery", fromlist=["build"]).build(
        "gmail", "v1", credentials=credentials, cache_discovery=False
    )
    email_address = service.users().getProfile(userId="me").execute()["emailAddress"]
    mailbox, _ = MailboxConnection.objects.update_or_create(
        organization=membership.organization,
        provider="gmail",
        email_address=email_address.lower(),
        defaults={
            "status": MailboxConnection.Status.ACTIVE,
            "encrypted_refresh_token": encrypt(credentials.refresh_token),
            "scopes": [READONLY_SCOPE],
            "policy_confirmed_at": timezone.now(),
        },
    )
    lead_source = None
    if lead_source_id:
        lead_source = get_object_or_404(
            LeadSource,
            id=lead_source_id,
            organization=membership.organization,
            source_type=LeadSource.SourceType.GMAIL,
        )
        lead_source.mailbox = mailbox
        lead_source.email_address = email_address.lower()
        lead_source.status = LeadSource.Status.READY
        lead_source.save(update_fields=["mailbox", "email_address", "status", "updated_at"])
    record_event(
        request,
        membership.organization,
        "source.connected",
        object_type="mailbox",
        object_id=str(mailbox.id),
        metadata={"provider": "gmail"},
    )
    messages.success(request, "Gmail source connected with read-only access.")
    if lead_source:
        return redirect(
            "project_source_detail",
            project_id=lead_source.project_id,
            source_id=lead_source.id,
        )
    return redirect("sources")
