from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from .connectors import iter_source
from .enrichment import FetchedPage, fetch_public_page
from .heuristics import CompiledProfile, active_profile
from .models import (
    BatchJob,
    Contact,
    ContactMetric,
    EnrichmentResult,
    EntityRelationship,
    LeadProject,
    LeadSource,
    MailboxConnection,
    ProductConcept,
    ProjectEntity,
    SourceMessage,
)
from .pipeline import ingest_rfc822


def _mailbox_for(source: LeadSource) -> MailboxConnection:
    if source.mailbox:
        return source.mailbox
    mailbox = MailboxConnection.objects.create(
        organization=source.organization,
        provider=source.source_type,
        email_address=source.email_address,
        status=MailboxConnection.Status.PAUSED,
        policy_confirmed_at=timezone.now()
        if source.source_type == LeadSource.SourceType.SYNTHETIC
        else None,
    )
    source.mailbox = mailbox
    source.save(update_fields=["mailbox", "updated_at"])
    return mailbox


CANCEL_CHECK_INTERVAL = 10


def _finish(job: BatchJob, status: str, error_code: str = "") -> None:
    job.status = status
    job.error_code = error_code
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "error_code", "finished_at", "updated_at"])


def _cancel_requested(job: BatchJob) -> bool:
    return (
        BatchJob.objects.filter(id=job.id).values_list("status", flat=True).first()
        == BatchJob.Status.CANCELLED
    )


def _maybe_enqueue_digest(job: BatchJob) -> None:
    """Auto-digest: chain an analysis run onto a successful sync when the project opts in.

    Hooked here rather than as a Celery chain so it behaves identically under
    eager mode and survives worker restarts. The one_active_job_per_target
    constraint collapses concurrent syncs onto a single pending digest.
    """
    project = job.project
    project.refresh_from_db()
    if not project.auto_digest_enabled or project.status != LeadProject.Status.ACTIVE:
        return
    try:
        with transaction.atomic():
            digest_job = BatchJob.objects.create(
                organization=job.organization,
                project=project,
                kind=BatchJob.Kind.ANALYZE,
                target_key="project",
                created_by=job.created_by,
            )
    except IntegrityError:
        return
    from .tasks import run_entity_analysis

    run_entity_analysis.delay(str(digest_job.id))


def execute_sync_job(job_id: str) -> None:
    job = BatchJob.objects.select_related("project", "source", "organization").get(id=job_id)
    if job.status == BatchJob.Status.CANCELLED:
        return
    if job.kind != BatchJob.Kind.SYNC or not job.source:
        _finish(job, BatchJob.Status.FAILED, "INVALID_SYNC_JOB")
        return
    source = job.source
    job.status = BatchJob.Status.RUNNING
    job.started_at = timezone.now()
    job.progress_total = source.max_messages_per_run
    job.rate_limit_remaining = source.rate_limit_per_minute
    job.save()
    source.status = LeadSource.Status.SYNCING
    source.save(update_fields=["status", "updated_at"])
    try:
        profile = active_profile(job.project)
        mailbox = _mailbox_for(source)
        for envelope in iter_source(source):
            if (
                job.progress_processed
                and job.progress_processed % CANCEL_CHECK_INTERVAL == 0
                and _cancel_requested(job)
            ):
                source.status = LeadSource.Status.READY
                source.save(update_fields=["status", "sync_cursor", "updated_at"])
                return
            result = ingest_rfc822(
                mailbox,
                envelope.provider_message_id,
                envelope.raw,
                labels=envelope.labels,
                provider_thread_id=envelope.thread_id,
                profile=profile,
            )
            job.progress_processed += 1
            job.requests_used += 1
            source.sync_cursor = envelope.cursor
            if result.opportunity:
                ProjectEntity.objects.get_or_create(
                    organization=job.organization,
                    project=job.project,
                    entity_type="opportunity",
                    entity_id=result.opportunity.id,
                )
            sender_email = result.message.sender.get("email", "")
            contact = Contact.objects.filter(
                organization=job.organization, primary_email=sender_email
            ).first()
            if contact:
                ProjectEntity.objects.get_or_create(
                    organization=job.organization,
                    project=job.project,
                    entity_type="contact",
                    entity_id=contact.id,
                )
                if contact.company_id:
                    ProjectEntity.objects.get_or_create(
                        organization=job.organization,
                        project=job.project,
                        entity_type="company",
                        entity_id=contact.company_id,
                    )
            job.save(
                update_fields=[
                    "progress_processed",
                    "requests_used",
                    "updated_at",
                ]
            )
        job.progress_total = job.progress_processed
        job.save(update_fields=["progress_total", "updated_at"])
        source.status = LeadSource.Status.READY
        source.last_synced_at = timezone.now()
        source.save(update_fields=["status", "sync_cursor", "last_synced_at", "updated_at"])
        _finish(job, BatchJob.Status.SUCCEEDED)
        _maybe_enqueue_digest(job)
    except PermissionError:
        source.status = LeadSource.Status.PAUSED
        source.save(update_fields=["status", "updated_at"])
        _finish(job, BatchJob.Status.BLOCKED, "NETWORK_POLICY_BLOCK")
    except Exception as exc:
        source.status = LeadSource.Status.ERROR
        source.last_error_code = type(exc).__name__.upper()[:100]
        source.save(update_fields=["status", "last_error_code", "updated_at"])
        _finish(job, BatchJob.Status.FAILED, source.last_error_code)


def _project_messages(job: BatchJob) -> list[SourceMessage]:
    mailbox_ids = list(
        job.project.sources.exclude(mailbox=None).values_list("mailbox_id", flat=True)
    )
    return list(
        SourceMessage.objects.filter(
            organization=job.organization,
            mailbox_id__in=mailbox_ids,
            safety_status=SourceMessage.Safety.CLEAN,
        ).order_by("sent_at", "created_at")
    )


def _message_contacts(job: BatchJob, message: SourceMessage) -> list[Contact]:
    addresses = [message.sender.get("email", "")]
    addresses.extend(item.get("email", "") for item in message.recipients)
    return list(
        Contact.objects.filter(
            organization=job.organization, primary_email__in=[a for a in addresses if a]
        )
    )


def _analyze_message(
    job: BatchJob,
    message: SourceMessage,
    contacts: list[Contact],
    profile: CompiledProfile,
) -> None:
    for contact in contacts:
        ProjectEntity.objects.get_or_create(
            organization=job.organization,
            project=job.project,
            entity_type="contact",
            entity_id=contact.id,
        )
    text = f"{message.subject}\n{message.body_text}"
    product_match = profile.product_pattern.search(text)
    if product_match:
        product_name = " ".join(product_match.group(1).split()).title()
        product, _ = ProductConcept.objects.get_or_create(
            organization=job.organization,
            canonical_name=product_name,
            defaults={"status": "candidate", "aliases": []},
        )
        ProjectEntity.objects.get_or_create(
            organization=job.organization,
            project=job.project,
            entity_type="product",
            entity_id=product.id,
        )
        for contact in contacts:
            role = "buyer" if message.direction == SourceMessage.Direction.INBOUND else "prospect"
            for candidate_role, pattern in profile.roles.items():
                if pattern.search(text):
                    role = candidate_role
                    break
            EntityRelationship.objects.get_or_create(
                organization=job.organization,
                project=job.project,
                source_type="contact",
                source_id=contact.id,
                target_type="product",
                target_id=product.id,
                relationship_type=role,
                defaults={
                    "confidence": Decimal("0.6000"),
                    "evidence_message": message,
                },
            )


def execute_analysis_job(job_id: str) -> None:
    job = BatchJob.objects.select_related("project", "organization").get(id=job_id)
    if job.status == BatchJob.Status.CANCELLED:
        return
    job.status = BatchJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at", "updated_at"])
    messages = _project_messages(job)
    job.progress_total = len(messages)
    job.save(update_fields=["progress_total", "updated_at"])
    try:
        profile = active_profile(job.project)
        contact_messages: dict[UUID, list[SourceMessage]] = {}
        for index, message in enumerate(messages):
            if index and index % CANCEL_CHECK_INTERVAL == 0 and _cancel_requested(job):
                return
            contacts = _message_contacts(job, message)
            for contact in contacts:
                contact_messages.setdefault(contact.id, []).append(message)
            # Each message commits on its own so progress and partial results
            # survive a mid-run failure or cancellation.
            with transaction.atomic():
                _analyze_message(job, message, contacts, profile)
            job.progress_processed += 1
            job.save(update_fields=["progress_processed", "updated_at"])

        if _cancel_requested(job):
            return
        _write_contact_metrics(job, contact_messages, profile)
        _finish(job, BatchJob.Status.SUCCEEDED)
    except Exception as exc:
        _finish(job, BatchJob.Status.FAILED, type(exc).__name__.upper()[:100])


@transaction.atomic
def _write_contact_metrics(
    job: BatchJob,
    contact_messages: dict[UUID, list[SourceMessage]],
    profile: CompiledProfile,
) -> None:
    for contact_id, related_messages in contact_messages.items():
        contact = Contact.objects.get(id=contact_id, organization=job.organization)
        dates = [item.sent_at for item in related_messages if item.sent_at]
        combined = "\n".join(f"{item.subject}\n{item.body_text}" for item in related_messages)
        topic_counts = Counter(
            topic for topic, pattern in profile.topics.items() for _ in pattern.finditer(combined)
        )
        positives = len(profile.positive.findall(combined))
        negatives = len(profile.negative.findall(combined))
        sentiment = (
            "positive"
            if positives > negatives
            else "negative"
            if negatives > positives
            else "neutral"
        )
        outcome_match = profile.outcome.search(combined)
        frequency = None
        if len(dates) > 1:
            span = max(dates) - min(dates)
            frequency = Decimal(str(round(span.total_seconds() / 86400 / (len(dates) - 1), 2)))
        inbound = sum(
            item.direction == SourceMessage.Direction.INBOUND for item in related_messages
        )
        outbound = sum(
            item.direction == SourceMessage.Direction.OUTBOUND for item in related_messages
        )
        quality = min(Decimal("100"), Decimal(len(related_messages) * 8 + bool(outcome_match) * 25))
        ContactMetric.objects.update_or_create(
            organization=job.organization,
            project=job.project,
            contact=contact,
            defaults={
                "contact_count": len(related_messages),
                "inbound_count": inbound,
                "outbound_count": outbound,
                "first_contact_at": min(dates) if dates else None,
                "last_contact_at": max(dates) if dates else None,
                "frequency_days": frequency,
                "main_topics": [topic for topic, _ in topic_counts.most_common(5)],
                "latest_outcome": outcome_match.group(0) if outcome_match else "",
                "sentiment": sentiment,
                "quality_score": quality,
            },
        )


def _contact_url(contact: Contact) -> str | None:
    if contact.company and contact.company.website:
        return contact.company.website
    if contact.company and contact.company.domain:
        return f"https://{contact.company.domain}/"
    return None


def execute_enrichment_job(
    job_id: str,
    *,
    fetcher: Callable[[str, list[str]], FetchedPage] = fetch_public_page,
    network_enabled: bool | None = None,
) -> None:
    job = BatchJob.objects.select_related("project", "organization").get(id=job_id)
    if job.status == BatchJob.Status.CANCELLED:
        return
    enabled = job.project.network_execution_enabled if network_enabled is None else network_enabled
    if not enabled:
        _finish(job, BatchJob.Status.BLOCKED, "NETWORK_POLICY_BLOCK")
        return
    job.status = BatchJob.Status.RUNNING
    job.started_at = timezone.now()
    job.progress_total = job.items.count()
    job.save()
    profile = active_profile(job.project)
    for item in job.items.all():
        if _cancel_requested(job):
            return
        if job.requests_used >= job.request_budget:
            item.status = "blocked"
            item.error_code = "BUDGET_EXHAUSTED"
            item.save(update_fields=["status", "error_code", "updated_at"])
            job.error_count += 1
            continue
        try:
            contact = Contact.objects.select_related("company").get(
                id=item.entity_id, organization=job.organization
            )
            url = _contact_url(contact)
            if not url:
                raise ValueError("NO_PUBLIC_URL")
            page = fetcher(url, job.project.allowed_domains)
            EnrichmentResult.objects.create(
                organization=job.organization,
                project=job.project,
                job_item=item,
                source_url=page.url,
                fetched_at=timezone.now(),
                content_sha256=page.content_sha256,
                candidate_data=page.candidate_data,
                extraction_profile_version=profile.version,
            )
            item.status = "succeeded"
            item.output = {"fields_found": sorted(page.candidate_data)}
        except (PermissionError, ValueError):
            item.status = "blocked"
            item.error_code = "URL_OR_SCOPE_BLOCK"
            job.error_count += 1
        except Exception as exc:
            item.status = "failed"
            item.error_code = type(exc).__name__.upper()[:100]
            job.error_count += 1
        item.save(update_fields=["status", "output", "error_code", "updated_at"])
        job.progress_processed += 1
        job.requests_used += 1
        job.save(
            update_fields=[
                "progress_processed",
                "requests_used",
                "error_count",
                "updated_at",
            ]
        )
    final_status = BatchJob.Status.PARTIAL if job.error_count else BatchJob.Status.SUCCEEDED
    _finish(job, final_status)
