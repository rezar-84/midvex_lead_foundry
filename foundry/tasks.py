from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from .gmail import iter_messages
from .models import MailboxConnection, SyncRun
from .pipeline import ingest_rfc822


@shared_task(bind=True, autoretry_for=(TimeoutError,), retry_backoff=True, max_retries=3)  # type: ignore[untyped-decorator]
def sync_gmail(self: object, mailbox_id: str, max_messages: int = 500) -> dict[str, int]:
    mailbox = MailboxConnection.objects.select_related("organization").get(id=mailbox_id)
    run = SyncRun.objects.create(
        organization=mailbox.organization, mailbox=mailbox, status="running"
    )
    try:
        for message in iter_messages(mailbox, max_messages=max_messages):
            try:
                ingest_rfc822(
                    mailbox,
                    message.message_id,
                    message.raw,
                    labels=message.labels,
                    provider_thread_id=message.thread_id,
                )
                run.processed_count += 1
                run.cursor_finished = message.history_id
            except (ValueError, UnicodeError):
                run.error_count += 1
            run.save(
                update_fields=["processed_count", "error_count", "cursor_finished", "updated_at"]
            )
        run.status = "completed"
        mailbox.history_cursor = run.cursor_finished
        mailbox.last_synced_at = timezone.now()
        mailbox.save(update_fields=["history_cursor", "last_synced_at", "updated_at"])
    except Exception:
        run.status = "failed"
        raise
    finally:
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "finished_at", "updated_at"])
    return {"processed": run.processed_count, "errors": run.error_count}
