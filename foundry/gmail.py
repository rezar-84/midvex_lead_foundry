from __future__ import annotations

import base64
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, cast

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from .crypto import decrypt
from .models import MailboxConnection

READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
OAUTH_TOKEN_URI = "https://oauth2.googleapis.com/token"  # noqa: S105  # nosec B105


@dataclass(frozen=True)
class GmailMessage:
    message_id: str
    thread_id: str
    raw: bytes
    labels: list[str]
    history_id: str


def require_real_data_enabled() -> None:
    if not settings.GMAIL_REAL_DATA_ENABLED:
        raise PermissionError("Real Gmail access is disabled by policy")
    if not all(
        [settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET, settings.GOOGLE_REDIRECT_URI]
    ):
        raise ImproperlyConfigured("Google OAuth settings are incomplete")


def oauth_flow(*, state: str | None = None) -> Flow:
    require_real_data_enabled()
    config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": OAUTH_TOKEN_URI,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        config, scopes=[READONLY_SCOPE], state=state, redirect_uri=settings.GOOGLE_REDIRECT_URI
    )


def authorization_url(state: str) -> str:
    flow = oauth_flow(state=state)
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return cast(str, url)


def _service(mailbox: MailboxConnection) -> Any:
    require_real_data_enabled()
    if mailbox.status != MailboxConnection.Status.ACTIVE or not mailbox.policy_confirmed_at:
        raise PermissionError("Mailbox must be active with a confirmed data policy")
    credentials = Credentials(
        token=None,
        refresh_token=decrypt(mailbox.encrypted_refresh_token),
        token_uri=OAUTH_TOKEN_URI,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=[READONLY_SCOPE],
    )
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def iter_messages(mailbox: MailboxConnection, *, max_messages: int = 500) -> Iterable[GmailMessage]:
    service: Any = _service(mailbox)
    page_token = None
    emitted = 0
    while emitted < max_messages:
        response = (
            service.users()
            .messages()
            .list(userId="me", pageToken=page_token, maxResults=min(100, max_messages - emitted))
            .execute()
        )
        for item in response.get("messages", []):
            payload = (
                service.users().messages().get(userId="me", id=item["id"], format="raw").execute()
            )
            raw = base64.urlsafe_b64decode(payload["raw"] + "===")
            yield GmailMessage(
                message_id=payload["id"],
                thread_id=payload.get("threadId", ""),
                raw=raw,
                labels=payload.get("labelIds", []),
                history_id=payload.get("historyId", ""),
            )
            emitted += 1
            if emitted >= max_messages:
                return
        page_token = response.get("nextPageToken")
        if not page_token:
            return
