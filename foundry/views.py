from __future__ import annotations

import os
import secrets
from typing import cast

import pyotp
import segno
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
from .pagination import paginate
from .runtime_settings import EDITABLE_KEYS, runtime_setting, set_runtime_setting


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
        name=request.user.get_username(), issuer_name=runtime_setting("FOUNDRY_BRAND_NAME")
    )
    qr_data_uri = segno.make(uri, error="m").svg_data_uri(scale=4)
    return render(
        request,
        "foundry/mfa_setup.html",
        {"form": form, "secret": secret, "provisioning_uri": uri, "qr_data_uri": qr_data_uri},
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
    page, querystring = paginate(request, items)
    return render(
        request,
        "foundry/conversations.html",
        {"conversations": page.object_list, "page_obj": page, "querystring": querystring},
    )


@login_required
@require_capability("view")
def knowledge(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    companies = (
        Company.objects.filter(organization=membership.organization)
        .prefetch_related("contacts")
        .order_by("name")
    )
    page, querystring = paginate(request, companies, per_page=24)
    return render(
        request,
        "foundry/knowledge.html",
        {"companies": page.object_list, "page_obj": page, "querystring": querystring},
    )


@login_required
@require_capability("view")
def opportunities(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    status = request.GET.get("status", OpportunityCandidate.Status.PENDING)
    valid = {choice for choice, _ in OpportunityCandidate.Status.choices}
    items = OpportunityCandidate.objects.filter(organization=membership.organization)
    if status in valid:
        items = items.filter(status=status)
    page, querystring = paginate(request, items.order_by("-score"), per_page=25)
    return render(
        request,
        "foundry/opportunities.html",
        {
            "opportunities": page.object_list,
            "status": status,
            "page_obj": page,
            "querystring": querystring,
        },
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
    auth_response = request.build_absolute_uri()
    # Force HTTPS scheme in environments where SSL is required,
    # to avoid oauthlib InsecureTransportError behind reverse proxies.
    if auth_response.startswith("http://") and os.environ.get("OAUTHLIB_INSECURE_TRANSPORT") != "1":
        auth_response = "https://" + auth_response[len("http://") :]
    flow.fetch_token(authorization_response=auth_response)
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


def _mask(value: str) -> str:
    if not value:
        return ""
    return f"{value[:4]}…{value[-2:]}" if len(value) > 8 else "set"


@login_required
@require_capability("manage_users")
def instance_settings(request: HttpRequest) -> HttpResponse:
    groups = [
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
    return render(
        request,
        "foundry/instance_settings.html",
        {"groups": groups, "editable_keys": set(EDITABLE_KEYS)},
    )


@login_required
@require_POST
@require_capability("manage_users")
def instance_setting_update(request: HttpRequest) -> HttpResponse:
    key = request.POST.get("key", "")
    if key not in EDITABLE_KEYS:
        messages.error(request, "That setting is not editable from the interface.")
        return redirect("instance_settings")
    value = request.POST.get("value", "").strip()
    set_runtime_setting(key, value)
    membership = request.membership  # type: ignore[attr-defined]
    record_event(
        request,
        membership.organization,
        "instance_setting.updated",
        object_type="instance_setting",
        object_id=key,
        metadata={"cleared": not value},
    )
    messages.success(
        request, f"{EDITABLE_KEYS[key].label} {'cleared' if not value else 'updated'}."
    )
    return redirect("instance_settings")
