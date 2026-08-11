from __future__ import annotations

import hashlib
import ipaddress
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from django.conf import settings
from lxml import html


def _user_agent() -> str:
    return str(settings.FOUNDRY_USER_AGENT)


@dataclass(frozen=True)
class FetchedPage:
    url: str
    content_sha256: str
    candidate_data: dict[str, object]


def validate_public_url(
    value: str,
    allowed_domains: list[str],
    *,
    resolver: Any = socket.getaddrinfo,
) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only absolute HTTP(S) URLs are allowed")
    host = parsed.hostname.lower().rstrip(".")
    if not any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains):
        raise PermissionError("URL is outside the project domain allowlist")
    if parsed.port and parsed.port not in {80, 443}:
        raise ValueError("Only standard HTTP(S) ports are allowed")
    addresses = {item[4][0] for item in resolver(host, parsed.port or 443, type=socket.SOCK_STREAM)}
    if not addresses:
        raise ValueError("Domain did not resolve")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise PermissionError("Private, reserved and local network targets are forbidden")
    return parsed.geturl()


def _extract_candidates(content: bytes, url: str) -> dict[str, object]:
    document = html.fromstring(content)
    title = " ".join(document.xpath("//title/text()")[:1]).strip()
    descriptions = document.xpath('//meta[@name="description"]/@content')
    emails = sorted(
        {
            href.removeprefix("mailto:").split("?", 1)[0]
            for href in document.xpath('//a[starts-with(@href,"mailto:")]/@href')
        }
    )
    social = sorted(
        {
            urljoin(url, href)
            for href in document.xpath("//a/@href")
            if any(domain in href for domain in ("linkedin.com", "instagram.com", "facebook.com"))
        }
    )
    return {
        "website": url,
        "title": title[:300],
        "description": (descriptions[0] if descriptions else "")[:1000],
        "emails": emails[:20],
        "social_urls": social[:20],
    }


def fetch_public_page(url: str, allowed_domains: list[str]) -> FetchedPage:
    if not settings.ENRICHMENT_NETWORK_ENABLED:
        raise PermissionError("Enrichment network execution is disabled by policy")
    if not settings.ENRICHMENT_EGRESS_PROXY:
        raise PermissionError("A private-network-blocking egress proxy is required")
    current = validate_public_url(url, allowed_domains)
    with httpx.Client(
        timeout=settings.ENRICHMENT_REQUEST_TIMEOUT,
        follow_redirects=False,
        proxy=settings.ENRICHMENT_EGRESS_PROXY,
    ) as client:
        robots_url = f"{urlparse(current).scheme}://{urlparse(current).netloc}/robots.txt"
        robots_response = client.get(robots_url, headers={"User-Agent": _user_agent()})
        parser = RobotFileParser()
        if robots_response.status_code < 400:
            parser.parse(robots_response.text.splitlines())
            if not parser.can_fetch(_user_agent(), current):
                raise PermissionError("robots.txt disallows this page")
        for _ in range(4):
            with client.stream("GET", current, headers={"User-Agent": _user_agent()}) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirect has no location")
                    current = validate_public_url(urljoin(current, location), allowed_domains)
                    continue
                response.raise_for_status()
                chunks = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > settings.ENRICHMENT_MAX_RESPONSE_BYTES:
                        raise ValueError("Response exceeds the enrichment size limit")
                    chunks.append(chunk)
                content = b"".join(chunks)
                return FetchedPage(
                    current,
                    hashlib.sha256(content).hexdigest(),
                    _extract_candidates(content, current),
                )
    raise ValueError("Too many redirects")
