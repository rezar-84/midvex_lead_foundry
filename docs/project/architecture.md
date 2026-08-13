---
status: draft
owner: architect
last-reviewed: 2026-08-13
---

# Technical architecture — Midvex Lead Foundry

## Shape

```text
browser (React SPA, frontend/) -> /api/ (django-ninja, session-authed)
browser -> Django web -> PostgreSQL
                    |-> Redis -> Celery workers/scheduler
                    |             |-> Gmail API / TLS IMAP / TLS POP3
                    |             |-> encrypted object storage
                    |             |-> Rspamd / ClamAV
                    |             `-> controlled egress proxy -> approved public sites/providers
                    `-> CSV destination
```

A modular monolith keeps authorisation, business rules and migrations in one deployable codebase. Since MVX-030..032 the interface is a React 19 + Vite + Tailwind SPA served by a Django catch-all view (built assets via WhiteNoise, multi-stage Docker build); it talks to a first-party JSON API under `/api/` (`foundry/api/`) that reuses the session, MFA middleware (401 JSON on `/api/*`), capability map and Django forms of the old views. Login/MFA pages, the CSV export POST and the Gmail OAuth handshake (`/integrations/gmail/…`) remain server-rendered/full-page. Slow, retryable work runs in Celery. Raw source evidence lives outside relational rows; PostgreSQL owns canonical relationships, reviews and provenance. PostgreSQL adjacency records and full-text/vector indexes avoid an early graph/search service.

## Components and boundaries

| Component | Responsibility | Owns | Depends on |
| --- | --- | --- | --- |
| accounts | MFA, organisation membership, roles | memberships/devices | Django auth |
| sources | OAuth/password connector lifecycle, TLS and checkpoints | source/mailbox/cursors | Gmail, IMAP, POP3; disabled externally |
| projects | purpose, retention, language, budgets and allowlists | project/source/job scope | accounts |
| operations | persisted sync, analysis, enrichment and dedup jobs; auto-digest chains analysis onto successful syncs for opted-in projects | progress/items/errors | Celery, sources, knowledge |
| ingestion | raw evidence and parsing | messages/attachments | object store, scanners |
| knowledge | entity resolution and graph | entities/edges/facts | ingestion |
| opportunities | rules, AI runs, review, digests | candidates/decisions | knowledge |
| api | first-party JSON surface for the SPA (`foundry/api/`) | schemas/routers/error contract | accounts, all domain services |
| data quality | contact dedup: exact auto-merge, fuzzy merge suggestions (`foundry/dedup.py`) | MergeSuggestion/merge audit | knowledge, operations |
| exports | previewed destination contracts | manifests/rows | approved candidates |

Views call organisation-scoped services; services call repositories/models; connector/provider implementations cannot bypass authorisation or write domain records directly. Mail/attachment content is untrusted data, never an instruction to a model or agent.

## External failure behavior

| Service | Failure behavior | Timeout/fallback |
| --- | --- | --- |
| Gmail | checkpoint and retry with backoff; revoked auth pauses mailbox | bounded request timeout; no alternate source |
| IMAP/POP3 | TLS-only standard ports, public-address validation, request pacing and bounded message count | pause with safe error; never delete source mail |
| Enrichment | allowlist, public-address validation, egress proxy, robots policy, byte/redirect/request budgets | disabled by default; candidate data only |
| Object storage | abort transaction/reference creation | bounded timeout; no local production fallback |
| Rspamd | mark assessment unavailable and hold from analysis | fail closed for new content |
| ClamAV | mark attachment unscanned and exclude | fail closed |
| AI/search | preserve deterministic results and show unavailable state | job budget/timeout; never fabricate |

Identity is established by Django's server session. Organisation membership and capability are checked at the service/object layer. Logs use correlation and opaque IDs; never content, contacts or credentials. Jobs are content-hash/version idempotent and observable by state/counts.

## Known limitations and non-goals

Pilot isolation is designed but not externally certified for SaaS. IMAP/POP3 and enrichment adapters exist behind disabled policy flags but have not been verified against real providers. No HA, third-party/public API (the `/api/` surface is first-party, same-origin and session-authenticated only), autonomous model training/action, CRM write, chat connector, or third-party analytics is authorised.
