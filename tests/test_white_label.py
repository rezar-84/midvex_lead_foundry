from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command

from foundry.connectors import SYNTHETIC_INTERNAL_ADDRESS, SYNTHETIC_INTERNAL_DOMAIN
from foundry.heuristics import compile_rules, default_profile, validate_field_rules
from foundry.models import (
    BatchJob,
    ContactMetric,
    ExtractionProfile,
    Membership,
    Organization,
    ProductConcept,
)
from foundry.operations import execute_analysis_job, execute_sync_job

from .test_project_operations import create_project


def _run_synthetic_pipeline(organization, project, settings, tmp_path):
    from foundry.models import LeadSource

    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    organization.internal_addresses = [SYNTHETIC_INTERNAL_ADDRESS]
    organization.internal_domains = [SYNTHETIC_INTERNAL_DOMAIN]
    organization.save()
    source = LeadSource.objects.create(
        organization=organization,
        project=project,
        source_type=LeadSource.SourceType.SYNTHETIC,
        name="Synthetic",
        email_address=SYNTHETIC_INTERNAL_ADDRESS,
        status=LeadSource.Status.READY,
    )
    user = get_user_model().objects.first()
    sync = BatchJob.objects.create(
        organization=organization,
        project=project,
        source=source,
        kind=BatchJob.Kind.SYNC,
        target_key=str(source.id),
        created_by=user,
    )
    execute_sync_job(str(sync.id))
    analysis = BatchJob.objects.create(
        organization=organization,
        project=project,
        kind=BatchJob.Kind.ANALYZE,
        target_key="project",
        created_by=user,
    )
    execute_analysis_job(str(analysis.id))
    return sync, analysis


@pytest.mark.django_db
def test_default_profile_reproduces_current_extraction(workspace, settings, tmp_path):
    organization, _, _, _ = workspace
    project = create_project(organization)
    sync, analysis = _run_synthetic_pipeline(organization, project, settings, tmp_path)

    sync.refresh_from_db()
    analysis.refresh_from_db()
    assert sync.status == BatchJob.Status.SUCCEEDED
    assert analysis.status == BatchJob.Status.SUCCEEDED
    product = ProductConcept.objects.get(organization=organization)
    assert "scanner" in product.canonical_name.lower()
    metric = ContactMetric.objects.get(project=project)
    assert "pricing" in metric.main_topics
    assert metric.sentiment == "positive"


@pytest.mark.django_db
def test_project_profile_override_changes_extraction(workspace, settings, tmp_path):
    organization, _, _, _ = workspace
    project = create_project(organization)
    ExtractionProfile.objects.create(
        organization=organization,
        project=project,
        entity_type="message",
        version=2,
        field_rules={"product_pattern": r"\b(widgetizer)\b"},
    )
    _run_synthetic_pipeline(organization, project, settings, tmp_path)

    # The override no longer matches "Nova scanner", so no product is extracted.
    assert not ProductConcept.objects.filter(organization=organization).exists()


def test_invalid_field_rules_are_rejected():
    with pytest.raises(ValidationError, match="not a valid pattern"):
        validate_field_rules({"product_pattern": "("})
    with pytest.raises(ValidationError, match="must be a regular-expression string"):
        validate_field_rules({"positive": 42})
    with pytest.raises(ValidationError, match="Unknown rule keys"):
        validate_field_rules({"surprise": ".*"})
    with pytest.raises(ValidationError, match="exceeds"):
        validate_field_rules({"negative": "x" * 501})
    with pytest.raises(ValidationError, match="must map labels to patterns"):
        validate_field_rules({"topics": ".*"})


def test_missing_keys_fall_back_to_defaults():
    profile = compile_rules({"positive": r"\b(splendid)\b"}, version=3)
    assert profile.version == 3
    assert profile.positive.search("splendid work")
    assert profile.opportunity.pattern == default_profile().opportunity.pattern


@pytest.mark.django_db
def test_provision_is_idempotent_and_never_echoes_password(capsys, monkeypatch):
    monkeypatch.setenv("FOUNDRY_ADMIN_PASSWORD", "a-very-secret-value")
    call_command("provision", "--org-name", "Acme Leads", "--username", "acme-admin")
    call_command("provision", "--org-name", "Acme Leads", "--username", "acme-admin")

    output = capsys.readouterr().out
    assert "a-very-secret-value" not in output
    organization = Organization.objects.get(slug="acme-leads")
    user = get_user_model().objects.get(username="acme-admin")
    assert user.check_password("a-very-secret-value")
    assert (
        Membership.objects.filter(
            organization=organization, user=user, role=Membership.Role.ADMIN, is_active=True
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_brand_name_flows_from_settings(mfa_session, settings):
    settings.FOUNDRY_BRAND_NAME = "Acme Lead Desk"
    response = mfa_session.get("/api/me")
    assert response.status_code == 200
    assert response.json()["brand_name"] == "Acme Lead Desk"
