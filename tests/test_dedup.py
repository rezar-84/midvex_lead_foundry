"""MVX-035: contact dedup — merge engine, dedup job, and merge-suggestion review."""

from __future__ import annotations

import pytest

from foundry.dedup import merge_contacts, normalize_email
from foundry.models import (
    AuditEvent,
    BatchJob,
    Company,
    Contact,
    ContactMetric,
    EntityTag,
    MergeSuggestion,
    ProjectEntity,
    Tag,
)
from foundry.operations import execute_dedup_job

from .test_project_operations import create_project


@pytest.fixture
def org(workspace):
    organization, user, _, _ = workspace
    return organization, user


def _contact(organization, email: str, name: str = "", **kwargs) -> Contact:
    return Contact.objects.create(
        organization=organization, primary_email=email, display_name=name, **kwargs
    )


@pytest.mark.django_db
def test_normalize_email():
    assert normalize_email("  Buyer@Example.TEST ") == "buyer@example.test"


@pytest.mark.django_db
def test_merge_contacts_repoints_and_folds(org):
    organization, _ = org
    project = create_project(organization)
    company = Company.objects.create(organization=organization, name="Acme")
    primary = _contact(organization, "buyer@acme.test", "Buyer")
    duplicate = _contact(organization, "buyer@acme2.test", "Buyer A", company=company, phone="123")

    ContactMetric.objects.create(
        organization=organization, project=project, contact=primary, contact_count=2
    )
    ContactMetric.objects.create(
        organization=organization, project=project, contact=duplicate, contact_count=3
    )
    for contact in (primary, duplicate):
        ProjectEntity.objects.create(
            organization=organization,
            project=project,
            entity_type="contact",
            entity_id=contact.id,
        )
    tag = Tag.objects.create(
        organization=organization, project=project, name="VIP", category="tier", color="#123456"
    )
    EntityTag.objects.create(
        organization=organization, tag=tag, entity_type="contact", entity_id=duplicate.id
    )

    merge_contacts(primary, duplicate, reason="test")

    primary.refresh_from_db()
    assert not Contact.objects.filter(id=duplicate.id).exists()
    assert primary.phone == "123"
    assert primary.company == company
    metric = ContactMetric.objects.get(project=project, contact=primary)
    assert metric.contact_count == 5
    # Duplicate's ProjectEntity row conflicted with primary's and was dropped.
    assert ProjectEntity.objects.filter(project=project, entity_type="contact").count() == 1
    assert EntityTag.objects.get(tag=tag).entity_id == primary.id
    assert AuditEvent.objects.filter(event_type="contact.merged").exists()


@pytest.mark.django_db
def test_dedup_job_merges_exact_and_suggests_fuzzy(org, workspace):
    organization, user = org
    project = create_project(organization)
    # Exact duplicates by normalized email.
    keep = _contact(organization, "buyer@acme.test", "Buyer")
    _contact(organization, "BUYER@ACME.TEST ", "Buyer Dup")
    # Fuzzy: same name, different email.
    _contact(organization, "d.karaca@corp.test", "Deniz Karaca")
    _contact(organization, "deniz@other.test", "Deniz Karaca")

    job = BatchJob.objects.create(
        organization=organization,
        project=project,
        kind=BatchJob.Kind.DEDUP,
        target_key="organization",
        created_by=user,
    )
    execute_dedup_job(str(job.id))
    job.refresh_from_db()

    assert job.status == BatchJob.Status.SUCCEEDED
    emails = set(
        Contact.objects.filter(organization=organization).values_list("primary_email", flat=True)
    )
    assert "buyer@acme.test" in emails
    assert keep.id in Contact.objects.values_list("id", flat=True)
    assert Contact.objects.filter(organization=organization).count() == 3
    suggestion = MergeSuggestion.objects.get(organization=organization)
    assert suggestion.reason == "same_name"
    assert suggestion.status == MergeSuggestion.Status.PENDING
    audit = AuditEvent.objects.filter(event_type="dedup.completed").get()
    assert audit.metadata["merged"] == 1
    assert audit.metadata["suggested"] == 1


@pytest.mark.django_db
def test_dedup_job_is_idempotent(org):
    organization, user = org
    project = create_project(organization)
    _contact(organization, "a.person@corp.test", "Alex Person")
    _contact(organization, "alex@other.test", "Alex Person")
    for _ in range(2):
        job = BatchJob.objects.create(
            organization=organization,
            project=project,
            kind=BatchJob.Kind.DEDUP,
            target_key="organization",
            created_by=user,
        )
        execute_dedup_job(str(job.id))
        job.refresh_from_db()
        assert job.status == BatchJob.Status.SUCCEEDED
    assert MergeSuggestion.objects.count() == 1


@pytest.mark.django_db
def test_suggestion_accept_merges_and_reject_suppresses(mfa_session, org):
    organization, _ = org
    primary = _contact(organization, "sam@corp.test", "Sam Seller")
    duplicate = _contact(organization, "sam.seller@corp2.test", "Sam Seller")
    suggestion = MergeSuggestion.objects.create(
        organization=organization,
        primary_contact=primary,
        duplicate_contact=duplicate,
        reason="same_name",
    )

    listing = mfa_session.get("/api/merge-suggestions")
    assert listing.status_code == 200
    assert listing.json()["count"] == 1

    response = mfa_session.post(
        f"/api/merge-suggestions/{suggestion.id}/decide",
        data={"decision": "accepted"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert not Contact.objects.filter(id=duplicate.id).exists()
    assert AuditEvent.objects.filter(event_type="merge_suggestion.decided").exists()

    # Deciding again is a 404 (no longer pending / row cascaded away).
    again = mfa_session.post(
        f"/api/merge-suggestions/{suggestion.id}/decide",
        data={"decision": "rejected"},
        content_type="application/json",
    )
    assert again.status_code == 404


@pytest.mark.django_db
def test_dedup_start_endpoint_requires_capability(mfa_session, client, org):
    organization, _ = org
    project = create_project(organization)
    response = mfa_session.post(f"/api/projects/{project.id}/dedup/start")
    assert response.status_code == 200
    assert response.json()["kind"] == "dedup"
