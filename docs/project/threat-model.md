---
status: draft
owner: security
last-reviewed: 2026-08-11
---

# Threat model — Midvex Lead Foundry

## Scope and assets

Covers local authentication, Gmail OAuth, ingestion, stored communications, scanners, AI/search boundaries, review and CSV export. Future IMAP/CRM/chat/SaaS connectors require revisions.

Highest-impact assets are OAuth/AI credentials, raw correspondence/attachments, cross-organisation isolation, derived relationship knowledge and truthful audit/evidence chains.

## Principal threats

| # | Threat | Mitigation | Enforced/tested at |
| --- | --- | --- | --- |
| T1 | Another user/organisation reads valid foreign IDs | mandatory organisation scope and uniform denial | services/querysets and authorisation tests |
| T2 | OAuth state/token theft or leakage | state validation, encrypted refresh token, redacted logs, revoke | connector callback/tests |
| T3 | Email prompt injection causes actions/data exfiltration | content-as-data boundary; no tools; structured schema | AI adapter/adversarial fixtures |
| T4 | Malicious MIME/archive exploits parser | content sniffing, limits, ClamAV, isolation, no execution | ingestion tests/scanner |
| T5 | AI invents a contact/opportunity | evidence constraint and human acceptance | pipeline/contract tests |
| T6 | CSV exports excessive/unreviewed data | role, accepted-only query, preview and manifest | export service/tests |
| T7 | Web fetch reaches private network | scheme/host/IP validation and redirect recheck | research client SSRF tests |
| T8 | Retry creates duplicates/cost storm | idempotency keys, content hashes, backoff and budgets | jobs/database tests |
| T9 | Deletion leaves derived copies | deletion inventory/job and post-purge verification | integration tests |

Different-organisation, revoked and tampered identifiers are denied without revealing existence. Abuse cases include mailbox/attachment bombs, repeated AI jobs, CSV scraping, password attacks and using research fetching as a proxy. Rate limits, budgets, MFA, size caps and explicit authorisation address them; SaaS residual risk remains gated by MVX-014.
