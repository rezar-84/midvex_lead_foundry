from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

from foundry.gmail import READONLY_SCOPE
from foundry.models import MailboxConnection


@pytest.mark.django_db
def test_gmail_callback_scheme_rewriting(mfa_session, workspace, settings, monkeypatch):
    """
    Test that the OAuth callback view rewrites http to https when
    OAUTHLIB_INSECURE_TRANSPORT is not set, preventing InsecureTransportError.
    """
    organization, user, membership, _ = workspace

    # 1. Enable Gmail features and set settings
    settings.GMAIL_REAL_DATA_ENABLED = True
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    settings.GOOGLE_CLIENT_SECRET = "test-client-secret"  # noqa: S105
    settings.GOOGLE_REDIRECT_URI = "https://mlf.midvex.com/sources/gmail/callback/"

    # Ensure OAUTHLIB_INSECURE_TRANSPORT is unset for the test
    monkeypatch.delenv("OAUTHLIB_INSECURE_TRANSPORT", raising=False)

    # 2. Setup session state to match the callback parameters
    session = mfa_session.session
    session["gmail_oauth_state"] = "test-state-123"
    session["gmail_policy_confirmed"] = True
    session.save()

    # Mock Flow and googleapiclient.discovery.build
    mock_credentials = MagicMock()
    mock_credentials.scopes = [READONLY_SCOPE]
    mock_credentials.refresh_token = "test-refresh-token"  # noqa: S105

    mock_flow = MagicMock()
    mock_flow.credentials = mock_credentials

    # We mock googleapiclient.discovery.build's return value
    mock_service = MagicMock()
    mock_service.users().getProfile(userId="me").execute.return_value = {
        "emailAddress": "user@gmail.com"
    }

    with (
        patch("foundry.views.oauth_flow", return_value=mock_flow),
        patch("googleapiclient.discovery.build", return_value=mock_service),
    ):
        # 3. Simulate callback hitting the server via HTTP (http://testserver/...)
        url = reverse("gmail_callback") + "?state=test-state-123&code=test-code"
        response = mfa_session.get(url)

        # Assert redirection back to the SPA sources page with the success flag
        assert response.status_code == 302
        assert response.url == "/sources?connected=1"

        # Assert flow.fetch_token was called with the rewritten HTTPS URL
        mock_flow.fetch_token.assert_called_once()
        called_args, called_kwargs = mock_flow.fetch_token.call_args
        auth_response = called_kwargs.get("authorization_response") or called_args[0]

        assert auth_response.startswith("https://testserver")

        # Verify mailbox is created and marked ACTIVE
        mailbox = MailboxConnection.objects.get(
            organization=organization, provider="gmail", email_address="user@gmail.com"
        )
        assert mailbox.status == MailboxConnection.Status.ACTIVE


@pytest.mark.django_db
def test_gmail_callback_scheme_no_rewriting_if_insecure_allowed(
    mfa_session, workspace, settings, monkeypatch
):
    """
    Test that the OAuth callback view does NOT rewrite http to https if
    OAUTHLIB_INSECURE_TRANSPORT is set to '1' (e.g. during local tests).
    """
    organization, user, membership, _ = workspace

    # Enable Gmail features
    settings.GMAIL_REAL_DATA_ENABLED = True
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    settings.GOOGLE_CLIENT_SECRET = "test-client-secret"  # noqa: S105
    settings.GOOGLE_REDIRECT_URI = "http://testserver/sources/gmail/callback/"

    # Set OAUTHLIB_INSECURE_TRANSPORT = 1
    monkeypatch.setenv("OAUTHLIB_INSECURE_TRANSPORT", "1")

    # Setup session state
    session = mfa_session.session
    session["gmail_oauth_state"] = "test-state-123"
    session["gmail_policy_confirmed"] = True
    session.save()

    mock_credentials = MagicMock()
    mock_credentials.scopes = [READONLY_SCOPE]
    mock_credentials.refresh_token = "test-refresh-token"  # noqa: S105

    mock_flow = MagicMock()
    mock_flow.credentials = mock_credentials

    mock_service = MagicMock()
    mock_service.users().getProfile(userId="me").execute.return_value = {
        "emailAddress": "user@gmail.com"
    }

    with (
        patch("foundry.views.oauth_flow", return_value=mock_flow),
        patch("googleapiclient.discovery.build", return_value=mock_service),
    ):
        # Simulate callback hitting HTTP
        url = reverse("gmail_callback") + "?state=test-state-123&code=test-code"
        response = mfa_session.get(url)

        assert response.status_code == 302

        mock_flow.fetch_token.assert_called_once()
        called_args, called_kwargs = mock_flow.fetch_token.call_args
        auth_response = called_kwargs.get("authorization_response") or called_args[0]

        # Verify it stays http
        assert auth_response.startswith("http://testserver")
