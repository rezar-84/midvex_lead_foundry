"""MVX-031: core-loop API endpoints — dashboard, opportunities, review, conversations, knowledge."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from foundry.models import (
    AuditEvent,
    Company,
    Contact,
    Membership,
    MFADevice,
    OpportunityCandidate,
    ReviewDecision,
)
from foundry.pipeline import ingest_rfc822


@pytest.fixture
def candidate(workspace, settings, tmp_path):
    _, _, _, mailbox = workspace
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    raw = (
        b"From: buyer@example.test\r\nTo: sales@internal.test\r\n"
        b"Subject: Quote request\r\n\r\nPlease send pricing.\r\n"
    )
    result = ingest_rfc822(mailbox, "api-core", raw).opportunity
    assert result is not None
    return result


@pytest.fixture
def analyst_session(client, workspace):
    organization, _, _, _ = workspace
    user = get_user_model().objects.create_user(
        username="analyst",
        password="a-strong-test-password",  # noqa: S106
    )
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.ANALYST)
    MFADevice.objects.create(
        user=user,
        encrypted_secret="test",  # noqa: S106
        confirmed_at="2026-01-01T00:00:00Z",
    )
    client.force_login(user)
    session = client.session
    session["mfa_verified"] = True
    session.save()
    return client


@pytest.mark.django_db
def test_dashboard_counts_and_recent(mfa_session, candidate):
    response = mfa_session.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pending_count"] == 1
    assert payload["accepted_count"] == 0
    assert payload["conversation_count"] == 1
    assert payload["recent"][0]["id"] == str(candidate.id)


@pytest.mark.django_db
def test_opportunities_list_filters_by_status(mfa_session, candidate):
    response = mfa_session.get("/api/opportunities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["title"] == candidate.title

    response = mfa_session.get("/api/opportunities?status=accepted")
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_opportunity_detail_includes_evidence(mfa_session, candidate):
    response = mfa_session.get(f"/api/opportunities/{candidate.id}")
    assert response.status_code == 200
    payload = response.json()
    evidence = payload["evidence"]
    assert evidence["subject"] == "Quote request"
    assert evidence["message_id"] == str(candidate.evidence_message_id)
    assert len(evidence["sha256"]) == 64


@pytest.mark.django_db
def test_opportunity_detail_scoped_to_organization(mfa_session, candidate):
    response = mfa_session.get("/api/opportunities/11111111-1111-1111-1111-111111111111")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.django_db
def test_review_records_decision_and_audit(mfa_session, candidate):
    response = mfa_session.post(
        f"/api/opportunities/{candidate.id}/review",
        data={"decision": "accepted", "note": "looks real"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    candidate.refresh_from_db()
    assert candidate.status == OpportunityCandidate.Status.ACCEPTED
    decision = ReviewDecision.objects.get(candidate=candidate)
    assert decision.note == "looks real"
    assert AuditEvent.objects.filter(
        event_type="opportunity.reviewed", object_id=str(candidate.id)
    ).exists()


@pytest.mark.django_db
def test_review_rejects_invalid_decision(mfa_session, candidate):
    response = mfa_session.post(
        f"/api/opportunities/{candidate.id}/review",
        data={"decision": "maybe"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.django_db
def test_analyst_cannot_review(analyst_session, candidate):
    response = analyst_session.post(
        f"/api/opportunities/{candidate.id}/review",
        data={"decision": "accepted"},
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.django_db
def test_conversations_list(mfa_session, candidate):
    response = mfa_session.get("/api/conversations")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["subject"] == "Quote request"


@pytest.mark.django_db
def test_knowledge_lists_companies_with_contacts(mfa_session, workspace):
    organization, _, _, _ = workspace
    company = Company.objects.create(organization=organization, name="Acme", domain="acme.test")
    Contact.objects.create(
        organization=organization,
        display_name="Buyer",
        primary_email="buyer@acme.test",
        company=company,
    )
    response = mfa_session.get("/api/knowledge")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["name"] == "Acme"
    assert payload["items"][0]["contacts"][0]["primary_email"] == "buyer@acme.test"
