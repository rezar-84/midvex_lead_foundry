import pytest
from django.contrib.auth import get_user_model

from foundry.models import MailboxConnection, Membership, MFADevice, Organization


@pytest.fixture
def workspace(db):
    organization = Organization.objects.create(
        name="Test Organisation",
        slug="test-org",
        retention_days=30,
        internal_addresses=["sales@internal.test"],
        internal_domains=["internal.test"],
    )
    user = get_user_model().objects.create_user(
        username="reviewer",
        password="a-strong-test-password",  # noqa: S106
    )
    membership = Membership.objects.create(
        organization=organization, user=user, role=Membership.Role.ADMIN
    )
    mailbox = MailboxConnection.objects.create(
        organization=organization,
        provider="synthetic",
        email_address="sales@internal.test",
        status=MailboxConnection.Status.PAUSED,
    )
    return organization, user, membership, mailbox


@pytest.fixture
def mfa_session(client, workspace):
    _, user, _, _ = workspace
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
