import hashlib

import pytest

from foundry.models import Contact, EvidenceCitation, OpportunityCandidate, SourceMessage
from foundry.pipeline import ingest_rfc822


@pytest.mark.django_db
@pytest.mark.integration
def test_ingest_creates_evidence_linked_candidate(workspace, settings, tmp_path):
    _, _, _, mailbox = workspace
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    raw = (
        b"From: Buyer <buyer@example.test>\r\nTo: sales@internal.test\r\n"
        b"Date: Mon, 7 Apr 2025 09:10:00 +0300\r\n"
        b"Message-ID: <quote@example.test>\r\nSubject: Pricing request\r\n\r\n"
        b"Please send a quotation and arrange a demo.\r\n"
    )

    result = ingest_rfc822(mailbox, "provider-1", raw, provider_thread_id="thread-1")

    assert result.created is True
    assert result.message.raw_sha256 == hashlib.sha256(raw).hexdigest()
    assert result.message.direction == SourceMessage.Direction.INBOUND
    assert result.opportunity is not None
    assert result.opportunity.evidence_message == result.message
    assert Contact.objects.get(primary_email="buyer@example.test").company.domain == "example.test"
    assert EvidenceCitation.objects.filter(message=result.message, locator="header:From").exists()


@pytest.mark.django_db
def test_ingest_is_idempotent(workspace, settings, tmp_path):
    _, _, _, mailbox = workspace
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    raw = (
        b"From: sender@example.test\r\nTo: sales@internal.test\r\n"
        b"Message-ID: <same@example.test>\r\nSubject: Hello\r\n\r\n"
        b"No commercial signal.\r\n"
    )

    first = ingest_rfc822(mailbox, "same", raw)
    second = ingest_rfc822(mailbox, "same", raw)

    assert first.created is True
    assert second.created is False
    assert SourceMessage.objects.count() == 1


@pytest.mark.django_db
def test_spam_is_quarantined_and_not_a_candidate(workspace, settings, tmp_path):
    _, _, _, mailbox = workspace
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    raw = (
        b"From: spam@example.test\r\nTo: sales@internal.test\r\nSubject: Pricing offer\r\n"
        b"X-Spam-Flag: YES\r\n\r\nRequest a demo.\r\n"
    )

    result = ingest_rfc822(mailbox, "spam", raw)

    assert result.message.safety_status == SourceMessage.Safety.QUARANTINED
    assert result.opportunity is None
    assert OpportunityCandidate.objects.count() == 0


@pytest.mark.django_db
def test_attachment_fails_closed_without_scanner(workspace, settings, tmp_path):
    _, _, _, mailbox = workspace
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    raw = (
        b"From: buyer@example.test\r\nTo: sales@internal.test\r\nSubject: Quote attached\r\n"
        b"MIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary=x\r\n\r\n--x\r\n"
        b"Content-Type: text/plain\r\n\r\nPlease send pricing.\r\n--x\r\n"
        b"Content-Type: application/pdf\r\nContent-Disposition: attachment; filename=quote.pdf\r\n"
        b"Content-Transfer-Encoding: base64\r\n\r\nJVBERg==\r\n--x--\r\n"
    )

    result = ingest_rfc822(mailbox, "attachment", raw)

    assert result.message.safety_status == SourceMessage.Safety.QUARANTINED
    assert result.message.attachments.get().scan_status == "scanner_unavailable"
    assert result.opportunity is None


@pytest.mark.django_db
def test_oversize_message_rejection_is_setting_driven(workspace, settings, tmp_path):
    _, _, _, mailbox = workspace
    settings.RAW_STORAGE_BACKEND = "filesystem"
    settings.RAW_STORAGE_ROOT = tmp_path
    settings.MAX_MESSAGE_BYTES = 128
    raw = (
        b"From: Buyer <buyer@example.test>\r\nTo: sales@internal.test\r\n"
        b"Subject: Pricing request\r\n\r\n" + b"x" * 200
    )

    with pytest.raises(ValueError, match="configured size limit"):
        ingest_rfc822(mailbox, "too-big", raw)

    settings.MAX_MESSAGE_BYTES = 25 * 1024 * 1024
    assert ingest_rfc822(mailbox, "fits-now", raw).created is True
