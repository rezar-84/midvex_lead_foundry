"""MVX-034: auto-digest — a successful sync chains an analysis job when the project opts in."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from foundry.connectors import SYNTHETIC_INTERNAL_ADDRESS, SYNTHETIC_INTERNAL_DOMAIN
from foundry.models import BatchJob, LeadProject, LeadSource
from foundry.operations import execute_sync_job

from .test_project_operations import create_project


@pytest.fixture
def synced_setup(workspace, settings, tmp_path):
    organization, user, _, _ = workspace
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    organization.internal_addresses = [SYNTHETIC_INTERNAL_ADDRESS]
    organization.internal_domains = [SYNTHETIC_INTERNAL_DOMAIN]
    organization.save()
    project = create_project(organization)
    source = LeadSource.objects.create(
        organization=organization,
        project=project,
        source_type=LeadSource.SourceType.SYNTHETIC,
        name="Synthetic",
        email_address=SYNTHETIC_INTERNAL_ADDRESS,
        status=LeadSource.Status.READY,
    )
    return organization, user, project, source


def _run_sync(organization, user, project, source) -> BatchJob:
    job = BatchJob.objects.create(
        organization=organization,
        project=project,
        source=source,
        kind=BatchJob.Kind.SYNC,
        target_key=str(source.id),
        created_by=user,
    )
    execute_sync_job(str(job.id))
    job.refresh_from_db()
    assert job.status == BatchJob.Status.SUCCEEDED
    return job


@pytest.mark.django_db
def test_auto_digest_enqueues_analysis_after_sync(synced_setup):
    organization, user, project, source = synced_setup
    project.auto_digest_enabled = True
    project.status = LeadProject.Status.ACTIVE
    project.save(update_fields=["auto_digest_enabled", "status"])

    _run_sync(organization, user, project, source)

    digest = BatchJob.objects.filter(project=project, kind=BatchJob.Kind.ANALYZE).first()
    assert digest is not None
    # Eager celery in tests runs the chained analysis to completion.
    assert digest.status == BatchJob.Status.SUCCEEDED
    assert digest.created_by == user


@pytest.mark.django_db
def test_no_digest_when_flag_disabled(synced_setup):
    organization, user, project, source = synced_setup
    _run_sync(organization, user, project, source)
    assert not BatchJob.objects.filter(project=project, kind=BatchJob.Kind.ANALYZE).exists()


@pytest.mark.django_db
def test_no_digest_for_inactive_project(synced_setup):
    organization, user, project, source = synced_setup
    project.auto_digest_enabled = True
    project.status = LeadProject.Status.PAUSED
    project.save(update_fields=["auto_digest_enabled", "status"])
    _run_sync(organization, user, project, source)
    assert not BatchJob.objects.filter(project=project, kind=BatchJob.Kind.ANALYZE).exists()


@pytest.mark.django_db
def test_digest_collapses_onto_existing_active_analysis(synced_setup):
    organization, user, project, source = synced_setup
    project.auto_digest_enabled = True
    project.status = LeadProject.Status.ACTIVE
    project.save(update_fields=["auto_digest_enabled", "status"])
    blocker = BatchJob.objects.create(
        organization=organization,
        project=project,
        kind=BatchJob.Kind.ANALYZE,
        target_key="project",
        status=BatchJob.Status.QUEUED,
        created_by=get_user_model().objects.get(pk=user.pk),
    )

    _run_sync(organization, user, project, source)  # must not raise

    analyses = BatchJob.objects.filter(project=project, kind=BatchJob.Kind.ANALYZE)
    assert analyses.count() == 1
    assert analyses.first() == blocker


@pytest.mark.django_db
def test_auto_digest_editable_via_project_api(mfa_session, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    response = mfa_session.patch(
        f"/api/projects/{project.id}",
        data={
            "name": project.name,
            "purpose": project.purpose,
            "status": project.status,
            "languages": ["en"],
            "retention_days": project.retention_days,
            "monthly_request_budget": project.monthly_request_budget,
            "allowed_domains_text": "",
            "network_execution_enabled": False,
            "auto_digest_enabled": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["auto_digest_enabled"] is True
    project.refresh_from_db()
    assert project.auto_digest_enabled is True
