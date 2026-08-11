import pytest
from django.core.exceptions import ValidationError

from foundry.gmail import require_real_data_enabled
from foundry.models import MailboxConnection, Organization


def test_real_gmail_is_disabled_by_default(settings):
    settings.GMAIL_REAL_DATA_ENABLED = False
    with pytest.raises(PermissionError, match="disabled by policy"):
        require_real_data_enabled()


@pytest.mark.django_db
def test_active_mailbox_requires_retention_policy():
    organization = Organization.objects.create(name="No policy", slug="no-policy")
    mailbox = MailboxConnection(
        organization=organization,
        email_address="mail@example.test",
        status=MailboxConnection.Status.ACTIVE,
    )
    with pytest.raises(ValidationError, match="retention policy"):
        mailbox.full_clean()
