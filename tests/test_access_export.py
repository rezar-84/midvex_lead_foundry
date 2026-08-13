import csv
import io

import pytest
from django.urls import reverse

from foundry.exports import accepted_candidates_csv
from foundry.models import OpportunityCandidate
from foundry.pipeline import ingest_rfc822


@pytest.mark.django_db
def test_anonymous_user_gets_unauthorized_from_api(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 401


@pytest.mark.django_db
def test_cross_organization_candidate_is_not_visible(mfa_session, workspace, settings, tmp_path):
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    response = mfa_session.get("/api/opportunities/11111111-1111-1111-1111-111111111111")
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.contract
def test_csv_only_contains_accepted_candidates(workspace, settings, tmp_path):
    organization, user, _, mailbox = workspace
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    raw = (
        b"From: buyer@example.test\r\nTo: sales@internal.test\r\n"
        b"Subject: Quote request\r\n\r\nPlease send pricing.\r\n"
    )
    candidate = ingest_rfc822(mailbox, "accepted", raw).opportunity
    assert candidate is not None
    candidate.status = OpportunityCandidate.Status.ACCEPTED
    candidate.save()

    batch, content = accepted_candidates_csv(organization, user)
    rows = list(csv.DictReader(io.StringIO(content)))

    assert batch.record_count == 1
    assert rows[0]["candidate_id"] == str(candidate.id)
    assert rows[0]["evidence_message_id"] == str(candidate.evidence_message_id)


@pytest.mark.django_db
@pytest.mark.e2e
def test_reviewer_accepts_then_exports_candidate(mfa_session, workspace, settings, tmp_path):
    _, _, _, mailbox = workspace
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    raw = (
        b"From: buyer@example.test\r\nTo: sales@internal.test\r\n"
        b"Subject: Proposal follow-up\r\n\r\nCan we arrange a meeting?\r\n"
    )
    candidate = ingest_rfc822(mailbox, "journey", raw).opportunity
    assert candidate is not None

    reviewed = mfa_session.post(
        f"/api/opportunities/{candidate.id}/review",
        data={"decision": "accepted", "note": "Relevant to the pilot"},
        content_type="application/json",
    )
    exported = mfa_session.post(reverse("export_csv"))

    candidate.refresh_from_db()
    assert reviewed.status_code == 200
    assert candidate.status == OpportunityCandidate.Status.ACCEPTED
    assert exported.status_code == 200
    assert str(candidate.id) in exported.content.decode()
