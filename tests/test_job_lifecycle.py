from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from foundry import operations
from foundry.connectors import (
    SYNTHETIC_INTERNAL_ADDRESS,
    SYNTHETIC_INTERNAL_DOMAIN,
)
from foundry.models import (
    BatchJob,
    BatchJobItem,
    LeadProject,
    LeadSource,
    Membership,
    MFADevice,
    Organization,
)
from foundry.operations import execute_analysis_job, execute_sync_job

from .test_project_operations import create_project


def _make_job(
    project: LeadProject,
    *,
    kind: str = BatchJob.Kind.ANALYZE,
    status: str = BatchJob.Status.QUEUED,
    source: LeadSource | None = None,
) -> BatchJob:
    user = get_user_model().objects.first()
    return BatchJob.objects.create(
        organization=project.organization,
        project=project,
        source=source,
        kind=kind,
        status=status,
        target_key=uuid.uuid4().hex,
        created_by=user,
    )


def _synced_project(mfa_session, organization, settings, tmp_path) -> LeadProject:
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    organization.internal_addresses = [SYNTHETIC_INTERNAL_ADDRESS]
    organization.internal_domains = [SYNTHETIC_INTERNAL_DOMAIN]
    organization.save()
    project = create_project(organization)
    mfa_session.post(
        reverse("project_source_create", args=[project.id]),
        {
            "source_type": "synthetic",
            "name": "Safe demo",
            "email_address": SYNTHETIC_INTERNAL_ADDRESS,
            "rate_limit_per_minute": 60,
            "max_messages_per_run": 50,
            "confirm_authority": "on",
        },
    )
    return project


@pytest.mark.django_db
def test_analysis_failure_persists_status_and_partial_progress(
    mfa_session, workspace, settings, tmp_path, monkeypatch
):
    organization, _, _, _ = workspace
    project = _synced_project(mfa_session, organization, settings, tmp_path)
    job = _make_job(project)

    calls = {"count": 0}
    original = operations._analyze_message

    def failing_analyze(job_arg, message, contacts, profile):
        calls["count"] += 1
        if calls["count"] >= 2:
            raise RuntimeError("boom")
        original(job_arg, message, contacts, profile)

    monkeypatch.setattr(operations, "_analyze_message", failing_analyze)
    execute_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == BatchJob.Status.FAILED
    assert job.error_code == "RUNTIMEERROR"
    assert job.finished_at is not None
    # Progress from the message that succeeded before the failure is persisted.
    assert job.progress_processed == 1


@pytest.mark.django_db
def test_cancel_queued_job_and_worker_skips_it(mfa_session, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    source = LeadSource.objects.create(
        organization=organization,
        project=project,
        source_type=LeadSource.SourceType.SYNTHETIC,
        name="Demo",
        email_address=SYNTHETIC_INTERNAL_ADDRESS,
    )
    job = _make_job(project, kind=BatchJob.Kind.SYNC, source=source)

    response = mfa_session.post(reverse("project_job_cancel", args=[project.id, job.id]))
    job.refresh_from_db()
    assert response.status_code == 302
    assert job.status == BatchJob.Status.CANCELLED
    assert job.finished_at is not None

    execute_sync_job(str(job.id))
    job.refresh_from_db()
    assert job.status == BatchJob.Status.CANCELLED
    assert job.progress_processed == 0


@pytest.mark.django_db
def test_cancel_refused_for_terminal_job(mfa_session, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    job = _make_job(project, status=BatchJob.Status.SUCCEEDED)

    response = mfa_session.post(
        reverse("project_job_cancel", args=[project.id, job.id]), follow=True
    )
    job.refresh_from_db()
    assert job.status == BatchJob.Status.SUCCEEDED
    assert "Only queued or running jobs can be cancelled." in response.content.decode()


@pytest.mark.django_db
def test_cancel_denied_without_run_batches_capability(client, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    job = _make_job(project)
    reviewer = get_user_model().objects.create_user(
        username="reviewer-2",
        password="a-strong-test-password",  # noqa: S106
    )
    Membership.objects.create(
        organization=organization, user=reviewer, role=Membership.Role.REVIEWER
    )
    MFADevice.objects.create(
        user=reviewer,
        encrypted_secret="test",  # noqa: S106
        confirmed_at="2026-01-01T00:00:00Z",
    )
    client.force_login(reviewer)
    session = client.session
    session["mfa_verified"] = True
    session.save()

    response = client.post(reverse("project_job_cancel", args=[project.id, job.id]))
    job.refresh_from_db()
    assert response.status_code == 403
    assert job.status == BatchJob.Status.QUEUED


@pytest.mark.django_db
def test_job_endpoints_hidden_from_foreign_organization(mfa_session, workspace):
    foreign_org = Organization.objects.create(
        name="Other Organisation", slug="other-org", retention_days=30
    )
    foreign_admin = get_user_model().objects.create_user(
        username="foreign-admin",
        password="a-strong-test-password",  # noqa: S106
    )
    Membership.objects.create(
        organization=foreign_org, user=foreign_admin, role=Membership.Role.ADMIN
    )
    foreign_project = create_project(foreign_org)
    foreign_job = _make_job(foreign_project)

    status_response = mfa_session.get(
        reverse("project_job_status", args=[foreign_project.id, foreign_job.id])
    )
    cancel_response = mfa_session.post(
        reverse("project_job_cancel", args=[foreign_project.id, foreign_job.id])
    )
    assert status_response.status_code == 404
    assert cancel_response.status_code == 404
    foreign_job.refresh_from_db()
    assert foreign_job.status == BatchJob.Status.QUEUED


@pytest.mark.django_db
def test_job_status_json_shape(mfa_session, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    job = _make_job(project, status=BatchJob.Status.RUNNING)
    job.progress_total = 4
    job.progress_processed = 1
    job.save(update_fields=["progress_total", "progress_processed"])

    response = mfa_session.get(reverse("project_job_status", args=[project.id, job.id]))
    data = response.json()
    assert response.status_code == 200
    assert data == {
        "status": "running",
        "status_display": "Running",
        "processed": 1,
        "total": 4,
        "percent": 25,
        "error_count": 0,
        "requests_used": 0,
        "request_budget": 0,
        "error_code": "",
        "terminal": False,
    }


@pytest.mark.django_db
def test_job_detail_items_paginate_and_clamp(mfa_session, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    job = _make_job(project, status=BatchJob.Status.SUCCEEDED)
    BatchJobItem.objects.bulk_create(
        [
            BatchJobItem(
                organization=organization,
                job=job,
                entity_type="contact",
                entity_id=uuid.uuid4(),
            )
            for _ in range(55)
        ]
    )

    first = mfa_session.get(reverse("project_job_detail", args=[project.id, job.id]))
    second = mfa_session.get(reverse("project_job_detail", args=[project.id, job.id]), {"page": 2})
    clamped = mfa_session.get(
        reverse("project_job_detail", args=[project.id, job.id]), {"page": 999}
    )
    assert len(first.context["items"]) == 50
    assert len(second.context["items"]) == 5
    assert clamped.context["page_obj"].number == 2
    assert "Entity results (55)" in first.content.decode()
