---
status: draft
owner: architect
last-reviewed: 2026-08-11
---

# Technical architecture — Midvex Lead Foundry

## Shape

```text
browser -> Django web -> PostgreSQL
                    |-> Redis -> Celery workers/scheduler
                    |             |-> Gmail API
                    |             |-> encrypted object storage
                    |             |-> Rspamd / ClamAV
                    |             `-> approved AI/search providers (disabled by default)
                    `-> CSV destination
```

A modular monolith keeps authorisation, business rules and migrations in one deployable codebase. Slow, retryable work runs in Celery. Raw source evidence lives outside relational rows; PostgreSQL owns canonical relationships, reviews and provenance. PostgreSQL adjacency records and full-text/vector indexes avoid an early graph/search service.

## Components and boundaries

| Component | Responsibility | Owns | Depends on |
| --- | --- | --- | --- |
| accounts | MFA, organisation membership, roles | memberships/devices | Django auth |
| sources | OAuth and connector lifecycle | mailbox/cursors | Gmail; later IMAP |
| ingestion | raw evidence and parsing | messages/attachments | object store, scanners |
| knowledge | entity resolution and graph | entities/edges/facts | ingestion |
| opportunities | rules, AI runs, review, digests | candidates/decisions | knowledge |
| exports | previewed destination contracts | manifests/rows | approved candidates |

Views call organisation-scoped services; services call repositories/models; connector/provider implementations cannot bypass authorisation or write domain records directly. Mail/attachment content is untrusted data, never an instruction to a model or agent.

## External failure behavior

| Service | Failure behavior | Timeout/fallback |
| --- | --- | --- |
| Gmail | checkpoint and retry with backoff; revoked auth pauses mailbox | bounded request timeout; no alternate source |
| Object storage | abort transaction/reference creation | bounded timeout; no local production fallback |
| Rspamd | mark assessment unavailable and hold from analysis | fail closed for new content |
| ClamAV | mark attachment unscanned and exclude | fail closed |
| AI/search | preserve deterministic results and show unavailable state | job budget/timeout; never fabricate |

Identity is established by Django's server session. Organisation membership and capability are checked at the service/object layer. Logs use correlation and opaque IDs; never content, contacts or credentials. Jobs are content-hash/version idempotent and observable by state/counts.

## Known limitations and non-goals

Pilot isolation is designed but not externally certified for SaaS. No HA, public API, autonomous action, CRM write, IMAP/chat connector, or third-party analytics is part of MVX-001–008.
