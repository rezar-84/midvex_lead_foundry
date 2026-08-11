from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime

from django.db import transaction
from django.utils import timezone

from .heuristics import CompiledProfile, default_profile
from .models import (
    Attachment,
    Company,
    Contact,
    Conversation,
    ConversationMessage,
    DerivedFact,
    EvidenceCitation,
    Interaction,
    MailboxConnection,
    OpportunityCandidate,
    SourceMessage,
    SpamAssessment,
)
from .storage import store_raw


@dataclass(frozen=True)
class IngestResult:
    message: SourceMessage
    created: bool
    opportunity: OpportunityCandidate | None


def _addresses(values: list[str]) -> list[dict[str, str]]:
    return [
        {"name": name, "email": address.lower()}
        for name, address in getaddresses(values)
        if address
    ]


def _body_text(message: EmailMessage) -> str:
    if message.is_multipart():
        parts = []
        for part in message.walk():
            if (
                part.get_content_type() == "text/plain"
                and part.get_content_disposition() != "attachment"
            ):
                try:
                    parts.append(part.get_content())
                except (LookupError, UnicodeDecodeError):
                    continue
        return "\n".join(parts)[:200_000]
    try:
        content = message.get_content()
        return content[:200_000] if isinstance(content, str) else ""
    except (LookupError, UnicodeDecodeError):
        return ""


def _direction(
    mailbox: MailboxConnection, sender: dict[str, str], recipients: list[dict[str, str]]
) -> str:
    internal = {value.lower() for value in mailbox.organization.internal_addresses}
    internal.add(mailbox.email_address.lower())
    sender_internal = sender.get("email", "").lower() in internal
    recipient_internal = any(item.get("email", "").lower() in internal for item in recipients)
    if sender_internal and recipient_internal:
        return SourceMessage.Direction.INTERNAL
    if sender_internal:
        return SourceMessage.Direction.OUTBOUND
    if recipient_internal:
        return SourceMessage.Direction.INBOUND
    return SourceMessage.Direction.UNKNOWN


def _spam(message: EmailMessage, labels: list[str]) -> tuple[str, Decimal | None, str]:
    if "SPAM" in {label.upper() for label in labels}:
        return "gmail", None, "reject"
    spam_flag = str(message.get("X-Spam-Flag", "")).upper()
    spam_status = str(message.get("X-Spam-Status", ""))
    if spam_flag == "YES" or spam_status.lower().startswith("yes"):
        score_match = re.search(r"score=(-?[\d.]+)", spam_status)
        score = Decimal(score_match.group(1)) if score_match else None
        return "header", score, "reject"
    return "none", None, "accept"


def _attachment_parts(message: EmailMessage) -> list[tuple[str, str, bytes]]:
    found = []
    for part in message.walk():
        if part.get_content_disposition() != "attachment":
            continue
        decoded = part.get_payload(decode=True)
        payload = decoded if isinstance(decoded, bytes) else b""
        found.append((part.get_filename() or "unnamed", part.get_content_type(), payload))
    return found


@transaction.atomic
def ingest_rfc822(
    mailbox: MailboxConnection,
    provider_message_id: str,
    raw: bytes,
    *,
    labels: list[str] | None = None,
    provider_thread_id: str = "",
    profile: CompiledProfile | None = None,
) -> IngestResult:
    if len(raw) > 25 * 1024 * 1024:
        raise ValueError("Message exceeds the configured size limit")
    existing = SourceMessage.objects.filter(
        mailbox=mailbox, provider_message_id=provider_message_id
    ).first()
    if existing:
        return IngestResult(
            existing,
            False,
            existing.conversationmessage.conversation.opportunities.first()
            if hasattr(existing, "conversationmessage")
            else None,
        )

    parsed = BytesParser(policy=policy.default).parsebytes(raw)
    sender_list = _addresses(parsed.get_all("From", []))
    sender = sender_list[0] if sender_list else {}
    recipients = _addresses(parsed.get_all("To", []) + parsed.get_all("Cc", []))
    date: datetime | None = None
    if parsed.get("Date"):
        try:
            date = parsedate_to_datetime(parsed["Date"])
            if date.tzinfo is None:
                date = timezone.make_aware(date)
        except (TypeError, ValueError, OverflowError):
            date = None
    body = _body_text(parsed)
    attachment_parts = _attachment_parts(parsed)
    stored = store_raw(mailbox.organization_id, provider_message_id, raw)
    labels = labels or []
    spam_source, spam_score, spam_action = _spam(parsed, labels)
    message = SourceMessage.objects.create(
        organization=mailbox.organization,
        mailbox=mailbox,
        provider_message_id=provider_message_id,
        provider_thread_id=provider_thread_id,
        internet_message_id=str(parsed.get("Message-ID", ""))[:998],
        subject=str(parsed.get("Subject", ""))[:998],
        sender=sender,
        recipients=recipients,
        sent_at=date,
        received_at=date,
        labels=labels,
        raw_object_key=stored.key,
        raw_sha256=stored.sha256,
        body_text=body,
        snippet=body[:500],
        safety_status=(
            SourceMessage.Safety.QUARANTINED
            if spam_action == "reject" or attachment_parts
            else SourceMessage.Safety.CLEAN
        ),
        direction=_direction(mailbox, sender, recipients),
    )
    SpamAssessment.objects.create(
        organization=mailbox.organization,
        message=message,
        source=spam_source,
        score=spam_score,
        action=spam_action,
    )
    for index, (filename, content_type, payload) in enumerate(attachment_parts):
        Attachment.objects.create(
            organization=mailbox.organization,
            message=message,
            filename=filename[:500],
            declared_content_type=content_type,
            size_bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            object_key=f"{stored.key}#part-{index}",
            scan_status="scanner_unavailable",
        )
    source_key = provider_thread_id or str(parsed.get("Message-ID", "")) or provider_message_id
    conversation, _ = Conversation.objects.get_or_create(
        organization=mailbox.organization,
        source_key=source_key,
        defaults={"subject": message.subject, "last_message_at": date},
    )
    if not conversation.last_message_at or (date and date > conversation.last_message_at):
        conversation.last_message_at = date
        conversation.save(update_fields=["last_message_at", "updated_at"])
    ConversationMessage.objects.create(
        organization=mailbox.organization, conversation=conversation, message=message
    )

    sender_email = sender.get("email", "").lower()
    internal_domains = {value.lower() for value in mailbox.organization.internal_domains}
    if "@" in sender_email and sender_email.rsplit("@", 1)[1] not in internal_domains:
        domain = sender_email.rsplit("@", 1)[1]
        company, _ = Company.objects.get_or_create(
            organization=mailbox.organization,
            domain=domain,
            defaults={"name": domain, "status": "candidate"},
        )
        contact, _ = Contact.objects.update_or_create(
            organization=mailbox.organization,
            primary_email=sender_email,
            defaults={
                "display_name": sender.get("name", ""),
                "company": company,
                "status": "candidate",
            },
        )
        fact, fact_created = DerivedFact.objects.get_or_create(
            organization=mailbox.organization,
            subject_type="contact",
            subject_id=contact.id,
            predicate="email_address",
            defaults={"value": {"email": sender_email}, "confidence": Decimal("1.0000")},
        )
        if fact_created:
            excerpt = str(parsed.get("From", ""))[:500]
            EvidenceCitation.objects.create(
                organization=mailbox.organization,
                fact=fact,
                message=message,
                locator="header:From",
                excerpt=excerpt,
                excerpt_sha256=hashlib.sha256(excerpt.encode()).hexdigest(),
            )

    opportunity = None
    rules = profile or default_profile()
    opportunity_terms = rules.opportunity
    exclusion_terms = rules.exclusion
    text = f"{message.subject}\n{body}"
    if (
        spam_action == "accept"
        and not attachment_parts
        and opportunity_terms.search(text)
        and not exclusion_terms.search(text)
    ):
        match = opportunity_terms.search(text)
        if match is None:
            return IngestResult(message, True, None)
        reason = f"Detected commercial intent term: {match.group(0)}"
        opportunity, _ = OpportunityCandidate.objects.get_or_create(
            organization=mailbox.organization,
            conversation=conversation,
            rule_code="commercial-intent-v1",
            defaults={
                "title": message.subject or "Potential commercial follow-up",
                "reason": reason,
                "score": Decimal("0.650"),
                "confidence": Decimal("0.6500"),
                "last_communication_at": date,
                "evidence_message": message,
            },
        )
        Interaction.objects.get_or_create(
            organization=mailbox.organization,
            conversation=conversation,
            interaction_type="commercial_intent",
            defaults={
                "occurred_at": date,
                "summary": reason,
                "confidence": Decimal("0.6500"),
            },
        )
    return IngestResult(message, True, opportunity)
