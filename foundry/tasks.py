from __future__ import annotations

from celery import shared_task

from .operations import (
    execute_analysis_job,
    execute_dedup_job,
    execute_enrichment_job,
    execute_sync_job,
)


@shared_task  # type: ignore[untyped-decorator]
def run_source_sync(job_id: str) -> None:
    execute_sync_job(job_id)


@shared_task  # type: ignore[untyped-decorator]
def run_entity_analysis(job_id: str) -> None:
    execute_analysis_job(job_id)


@shared_task  # type: ignore[untyped-decorator]
def run_entity_enrichment(job_id: str) -> None:
    execute_enrichment_job(job_id)


@shared_task  # type: ignore[untyped-decorator]
def run_contact_dedup(job_id: str) -> None:
    execute_dedup_job(job_id)
