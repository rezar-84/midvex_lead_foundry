from __future__ import annotations

import imaplib
import ipaddress
import poplib
import socket
import ssl
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from .crypto import decrypt
from .gmail import iter_messages
from .models import LeadSource


@dataclass(frozen=True)
class SourceEnvelope:
    provider_message_id: str
    thread_id: str
    raw: bytes
    labels: list[str]
    cursor: str


class RateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        self.minimum_interval = 60 / requests_per_minute
        self.previous_request = 0.0

    def wait(self) -> None:
        remaining = self.minimum_interval - (time.monotonic() - self.previous_request)
        if remaining > 0:
            time.sleep(remaining)
        self.previous_request = time.monotonic()


def _require_network(source: LeadSource) -> None:
    if not settings.SOURCE_NETWORK_ENABLED or not source.project.network_execution_enabled:
        raise PermissionError("External source execution is disabled by policy")
    if source.status == LeadSource.Status.REVOKED:
        raise PermissionError("Source credentials were revoked")
    if source.source_type in {LeadSource.SourceType.IMAP, LeadSource.SourceType.POP3}:
        validate_public_mail_host(source.host)


def validate_public_mail_host(host: str, *, resolver: Any = socket.getaddrinfo) -> None:
    addresses = {item[4][0] for item in resolver(host, None, type=socket.SOCK_STREAM)}
    if not addresses:
        raise ValueError("Mail source host did not resolve")
    if any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise PermissionError("Private, reserved and local mail targets are forbidden")


def _synthetic_messages() -> Iterator[SourceEnvelope]:
    samples = [
        b"From: Deniz Buyer <deniz@example.test>\r\nTo: sales@midvex.test\r\n"
        b"Date: Mon, 7 Apr 2025 09:10:00 +0300\r\nMessage-ID: <project-demo-1@example.test>\r\n"
        b"Subject: Dental scanner quotation\r\n\r\n"
        b"We are a buyer interested in the Nova scanner product. "
        b"Please send pricing and arrange a demo.\r\n",
        b"From: sales@midvex.test\r\nTo: Deniz Buyer <deniz@example.test>\r\n"
        b"Date: Wed, 9 Apr 2025 10:00:00 +0300\r\nMessage-ID: <project-demo-2@midvex.test>\r\n"
        b"Subject: Re: Dental scanner quotation\r\n\r\n"
        b"Thank you. We sent the proposal and will follow up next week.\r\n",
    ]
    for index, raw in enumerate(samples, start=1):
        yield SourceEnvelope(f"synthetic-{index}", "synthetic-thread-1", raw, [], str(index))


def _imap_messages(source: LeadSource) -> Iterator[SourceEnvelope]:
    _require_network(source)
    limiter = RateLimiter(source.rate_limit_per_minute)
    context = ssl.create_default_context()
    with imaplib.IMAP4_SSL(source.host, source.port or 993, ssl_context=context) as client:
        client.login(source.username, decrypt(source.encrypted_password))
        status, _ = client.select("INBOX", readonly=True)
        if status != "OK":
            raise RuntimeError("IMAP_SELECT_FAILED")
        status, data = client.uid("search", None, "ALL")  # type: ignore[arg-type]
        if status != "OK" or not data:
            raise RuntimeError("IMAP_SEARCH_FAILED")
        cursor = int(source.sync_cursor or 0)
        uids = [int(uid) for uid in data[0].split() if int(uid) > cursor]
        for uid in uids[: source.max_messages_per_run]:
            limiter.wait()
            status, payload = client.uid("fetch", str(uid), "(BODY.PEEK[])")
            if status != "OK" or not payload or not isinstance(payload[0], tuple):
                continue
            raw = payload[0][1]
            if isinstance(raw, bytes):
                yield SourceEnvelope(f"imap:{uid}", "", raw, [], str(uid))


def _pop3_messages(source: LeadSource) -> Iterator[SourceEnvelope]:
    _require_network(source)
    limiter = RateLimiter(source.rate_limit_per_minute)
    context = ssl.create_default_context()
    client = poplib.POP3_SSL(source.host, source.port or 995, context=context)
    try:
        client.user(source.username)
        client.pass_(decrypt(source.encrypted_password))
        _, entries, _ = client.uidl()
        for entry in entries[: source.max_messages_per_run]:
            number, uid = entry.decode("ascii").split(maxsplit=1)
            limiter.wait()
            _, lines, _ = client.retr(int(number))
            yield SourceEnvelope(f"pop3:{uid}", "", b"\r\n".join(lines) + b"\r\n", [], uid)
    finally:
        client.quit()


def iter_source(source: LeadSource) -> Iterator[SourceEnvelope]:
    if source.source_type == LeadSource.SourceType.SYNTHETIC:
        yield from _synthetic_messages()
        return
    if source.source_type == LeadSource.SourceType.GMAIL:
        _require_network(source)
        if not source.mailbox:
            raise PermissionError("Gmail OAuth authorization is incomplete")
        for message in iter_messages(source.mailbox, max_messages=source.max_messages_per_run):
            yield SourceEnvelope(
                message.message_id,
                message.thread_id,
                message.raw,
                message.labels,
                message.history_id,
            )
        return
    if source.source_type == LeadSource.SourceType.IMAP:
        yield from _imap_messages(source)
        return
    if source.source_type == LeadSource.SourceType.POP3:
        yield from _pop3_messages(source)
        return
    raise ValueError("Unsupported lead source type")
