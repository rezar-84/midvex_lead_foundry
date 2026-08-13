from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model

from foundry.connectors import (
    SYNTHETIC_INTERNAL_ADDRESS,
    SYNTHETIC_INTERNAL_DOMAIN,
    validate_public_mail_host,
)
from foundry.crypto import decrypt
from foundry.enrichment import FetchedPage, validate_public_url
from foundry.models import (
    BatchJob,
    BatchJobItem,
    Company,
    Contact,
    ContactMetric,
    EnrichmentResult,
    EntityTag,
    LeadProject,
    LeadSource,
    Membership,
    MFADevice,
    Organization,
    ProductConcept,
    ProjectEntity,
)
from foundry.operations import execute_enrichment_job


def create_project(organization: Organization, *, network: bool = False) -> LeadProject:
    return LeadProject.objects.create(
        organization=organization,
        name="Archive recovery",
        slug=f"archive-{uuid.uuid4().hex[:8]}",
        purpose="Recover missed opportunities from authorised synthetic messages.",
        status=LeadProject.Status.ACTIVE,
        languages=["en", "tr"],
        retention_days=30,
        monthly_request_budget=100,
        allowed_domains=["example.test"],
        network_execution_enabled=network,
    )


@pytest.mark.django_db
def test_admin_creates_organization_scoped_project(mfa_session, workspace):
    organization, _, _, _ = workspace
    response = mfa_session.post(
        "/api/projects",
        data={
            "name": "Nine year archive",
            "purpose": "Find reviewable historical opportunities.",
            "status": "draft",
            "languages": ["en", "tr"],
            "retention_days": 90,
            "monthly_request_budget": 250,
            "allowed_domains_text": "example.test\ncompany.test",
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    project = LeadProject.objects.get(name="Nine year archive")
    payload = response.json()
    assert payload["id"] == str(project.id)
    assert payload["slug"] == project.slug
    assert project.organization == organization
    assert project.allowed_domains == ["company.test", "example.test"]
    assert project.network_execution_enabled is False


@pytest.mark.django_db
def test_analyst_cannot_create_project(client, workspace):
    organization, _, _, _ = workspace
    analyst = get_user_model().objects.create_user(username="analyst")
    Membership.objects.create(organization=organization, user=analyst, role=Membership.Role.ANALYST)
    MFADevice.objects.create(
        user=analyst,
        encrypted_secret="confirmed-for-middleware-only",  # noqa: S106
        confirmed_at="2026-01-01T00:00:00Z",
    )
    client.force_login(analyst)
    session = client.session
    session["mfa_verified"] = True
    session.save()

    response = client.post(
        "/api/projects",
        data={"name": "Blocked project"},
        content_type="application/json",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert not LeadProject.objects.filter(name="Blocked project").exists()


@pytest.mark.django_db
def test_imap_source_requires_tls_and_encrypts_password(mfa_session, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    url = f"/api/projects/{project.id}/sources"
    payload = {
        "source_type": "imap",
        "name": "Company archive",
        "email_address": "archive@example.test",
        "host": "mail.example.test",
        "port": 993,
        "username": "archive@example.test",
        "password": "application-password",
        "rate_limit_per_minute": 30,
        "max_messages_per_run": 100,
        "confirm_authority": True,
    }
    insecure = mfa_session.post(url, data=payload, content_type="application/json")
    assert insecure.status_code == 400
    error = insecure.json()["error"]
    assert error["code"] == "validation_error"
    assert any(
        "TLS is mandatory" in message
        for messages in error["fields"].values()
        for message in messages
    )
    assert LeadSource.objects.count() == 0

    secure = mfa_session.post(
        url, data={**payload, "use_tls": True}, content_type="application/json"
    )
    assert secure.status_code == 200
    source = LeadSource.objects.get()
    assert secure.json()["source"]["id"] == str(source.id)

    detail = mfa_session.get(f"/api/projects/{project.id}/sources/{source.id}")
    assert detail.status_code == 200
    assert "application-password" not in source.encrypted_password
    assert decrypt(source.encrypted_password) == "application-password"
    assert "application-password" not in detail.content.decode()
    assert detail.json()["has_password"] is True


@pytest.mark.django_db
@pytest.mark.e2e
def test_synthetic_project_sync_analysis_and_entity_api(mfa_session, workspace, settings, tmp_path):
    organization, _, _, _ = workspace
    organization.internal_addresses = [SYNTHETIC_INTERNAL_ADDRESS]
    organization.internal_domains = [SYNTHETIC_INTERNAL_DOMAIN]
    organization.save()
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    project = create_project(organization)
    sync_response = mfa_session.post(
        f"/api/projects/{project.id}/sources",
        data={
            "source_type": "synthetic",
            "name": "Safe demo",
            "email_address": SYNTHETIC_INTERNAL_ADDRESS,
            "rate_limit_per_minute": 60,
            "max_messages_per_run": 50,
            "confirm_authority": True,
        },
        content_type="application/json",
    )
    assert sync_response.status_code == 200
    assert sync_response.json()["job_id"]

    analysis_response = mfa_session.post(f"/api/projects/{project.id}/analysis/start")
    assert analysis_response.status_code == 200
    assert BatchJob.objects.filter(project=project, status=BatchJob.Status.SUCCEEDED).count() == 2

    contacts_response = mfa_session.get(f"/api/projects/{project.id}/contacts")
    assert contacts_response.status_code == 200
    rows = contacts_response.json()["items"]
    row = next(item for item in rows if item["display_name"] == "Deniz Buyer")
    assert "buyer" in {product["relationship_type"] for product in row["products"]}
    assert ContactMetric.objects.filter(project=project, scoring_version="heuristic-v1").exists()

    assert ProductConcept.objects.filter(canonical_name__icontains="scanner").exists()
    products_response = mfa_session.get(f"/api/projects/{project.id}/products")
    assert any(
        "scanner" in product["canonical_name"].lower()
        for product in products_response.json()["items"]
    )

    contact = Contact.objects.get(primary_email="deniz@example.test")
    contact_detail_response = mfa_session.get(f"/api/projects/{project.id}/contacts/{contact.id}")
    assert contact_detail_response.status_code == 200
    assert "enrichment_results" in contact_detail_response.json()

    tag_response = mfa_session.post(
        f"/api/projects/{project.id}/tags",
        data={"name": "High priority", "category": "priority", "color": "#466653"},
        content_type="application/json",
    )
    assert tag_response.status_code == 200
    tag_payload = tag_response.json()
    assert tag_payload["name"] == "High priority"

    assign_response = mfa_session.post(
        f"/api/projects/{project.id}/contacts/tags/assign",
        data={"contact_ids": [str(contact.id)], "tag_id": tag_payload["id"]},
        content_type="application/json",
    )
    assert assign_response.status_code == 200
    assert assign_response.json() == {"assigned": 1}
    assert EntityTag.objects.filter(tag_id=tag_payload["id"], entity_id=contact.id).exists()


def test_private_enrichment_target_is_rejected():
    def private_resolver(*args: object, **kwargs: object) -> list[tuple[object, ...]]:
        return [(None, None, None, None, ("127.0.0.1", 443))]

    with pytest.raises(PermissionError, match="Private"):
        validate_public_url(
            "https://example.test/profile", ["example.test"], resolver=private_resolver
        )


def test_private_mail_source_target_is_rejected():
    def private_resolver(*args: object, **kwargs: object) -> list[tuple[object, ...]]:
        return [(None, None, None, None, ("10.0.0.5", 993))]

    with pytest.raises(PermissionError, match="Private"):
        validate_public_mail_host("mail.example.test", resolver=private_resolver)


@pytest.mark.django_db
@pytest.mark.integration
def test_enrichment_stores_provenance_candidates_with_mocked_fetcher(workspace, mfa_session):
    organization, user, _, _ = workspace
    project = create_project(organization, network=True)
    company = Company.objects.create(
        organization=organization,
        name="Example",
        domain="example.test",
        website="https://example.test/",
    )
    contact = Contact.objects.create(
        organization=organization,
        display_name="Public Contact",
        primary_email="contact@example.test",
        company=company,
    )
    ProjectEntity.objects.create(
        organization=organization,
        project=project,
        entity_type="contact",
        entity_id=contact.id,
    )
    job = BatchJob.objects.create(
        organization=organization,
        project=project,
        kind=BatchJob.Kind.ENRICH,
        target_key="contacts",
        request_budget=1,
        created_by=user,
    )
    BatchJobItem.objects.create(
        organization=organization, job=job, entity_type="contact", entity_id=contact.id
    )

    def mocked_fetcher(url: str, allowed: list[str]) -> FetchedPage:
        assert url == "https://example.test/"
        assert allowed == ["example.test"]
        return FetchedPage(url, "a" * 64, {"website": url, "title": "Example"})

    execute_enrichment_job(str(job.id), fetcher=mocked_fetcher, network_enabled=True)

    job.refresh_from_db()
    result = EnrichmentResult.objects.get(job_item__job=job)
    review = mfa_session.post(
        f"/api/projects/{project.id}/enrichment/{result.id}/review",
        data={"decision": "accepted"},
        content_type="application/json",
    )
    result.refresh_from_db()
    detail = mfa_session.get(f"/api/projects/{project.id}/contacts/{contact.id}")
    assert job.status == BatchJob.Status.SUCCEEDED
    assert review.status_code == 200
    assert review.json()["status"] == "accepted"
    assert result.status == "accepted"
    enrichment_results = detail.json()["enrichment_results"]
    assert enrichment_results[0]["candidate_data"]["title"] == "Example"
    assert enrichment_results[0]["status"] == "accepted"
    assert result.content_sha256 == "a" * 64
    assert result.candidate_data["title"] == "Example"


@pytest.mark.django_db
def test_external_source_sync_is_blocked_by_default(workspace):
    organization, user, _, _ = workspace
    project = create_project(organization)
    source = LeadSource.objects.create(
        organization=organization,
        project=project,
        source_type=LeadSource.SourceType.IMAP,
        name="Blocked source",
        email_address="archive@example.test",
        host="mail.example.test",
        port=993,
        username="archive@example.test",
        encrypted_password="not-used",  # noqa: S106
        use_tls=True,
    )
    job = BatchJob.objects.create(
        organization=organization,
        project=project,
        source=source,
        kind=BatchJob.Kind.SYNC,
        target_key=str(source.id),
        created_by=user,
    )

    from foundry.operations import execute_sync_job

    execute_sync_job(str(job.id))

    job.refresh_from_db()
    assert job.status == BatchJob.Status.BLOCKED
    assert job.error_code == "NETWORK_POLICY_BLOCK"
