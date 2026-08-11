---
status: active
owner: architect
last-reviewed: 2026-08-11
---

# Worklog — midvex_lead_foundry

> Append-only. **Newest entry at the top.** One entry per completed work item, written
> at the LOG step of the loop, using `../templates/worklog-entry.md`.
>
> This is where a future reader — human or agent — learns *why* the system looks the way
> it does, what was actually verified, and what is still wrong. The backlog says what;
> this says why, and what it cost.

**Rules**

- Every entry names its `MVX-###`.
- **Never rewrite history.** If an entry was wrong, append a correction that references
  it. The record of a mistaken belief is part of the record.
- The **Not done** section is mandatory. Deferred, stubbed, mocked, and hardcoded things
  are listed with follow-up IDs. An entry with no "Not done" section is either
  exceptional or incomplete, and it is usually the second.
- Verification is reported with real commands and real results. "Tests pass" is not a
  verification record.
- When this file gets long, move older entries to `worklog-archive/YYYY.md` and leave a
  pointer here. Do not truncate.

---

<!-- New entries go here, above the older ones. -->

## MVX-001 — governed standalone synthetic pilot foundation

**Date:** 2026-08-11 **Tier:** 1
**Status:** Parked
**Branch/commits:** `feat/MVX-001-bootstrap-lead-foundry` / uncommitted; merge requires two named human approvals

### What changed

Replaced the generic project placeholders with a standalone Gmail-first product charter, backlog, requirements, architecture, data/security/test/release artifacts, four ADRs and Tier 1 reviews. Added a Django/Celery synthetic MVP with local accounts, mandatory TOTP MFA, organisation roles, evidence storage/hashes, RFC 822 ingestion, spam and attachment quarantine, evidence-linked identity knowledge, deterministic candidates, review decisions, accepted-only CSV v1, a disabled-by-default Gmail read-only connector, Dokploy-oriented containers and synthetic tests.

### Why

The archive contains personal communications and the destination CRM is not yet the system of record. A standalone modular monolith keeps the first review loop small while immutable evidence and disabled external processing prevent inferred leads from being mistaken for source truth or real data from being processed before authority is known.

### Verified

- [x] `checks.format` — **Verified** — `ruff format --check .`: 35 files already formatted.
- [x] `checks.lint` — **Verified** — `ruff check .`: all checks passed; Ruff emitted its Python 3.14 preview warning.
- [x] `checks.typecheck` — **Verified** — mypy found no issues in 25 source files.
- [x] `checks.unit` — **Verified** — 8 passed, 2 deselected.
- [x] `checks.integration` — **Verified** — 1 passed, 9 deselected.
- [x] `checks.contract` — **Verified** — 1 passed, 9 deselected.
- [x] `checks.build` — **Verified** — source distribution and wheel built successfully.
- [x] `checks.scan` — **Verified** — Bandit completed with no findings. The initial audit found five advisories in cryptography 46.0.7 and pytest 8.4.2; upgrades to 50.0.0 and 9.1.1 were locked, and the repeated audit reported no known vulnerabilities. The private package itself was skipped because it is not on PyPI.
- [x] `checks.a11y` — **Verified** — static checks passed for 11 templates.
- [x] `checks.e2e` — **Verified** — 1 passed, 9 deselected; a reviewer accepted an evidence candidate and downloaded its CSV record.
- [x] manual — **Verified** — Django system check reported no issues; migration dry-run reported no changes. Production deploy check with a deliberately weak synthetic key reported W009 and the intentionally unset HSTS preload W021; no production environment was exercised.

### Not done

- Account recovery, membership lifecycle and expanded audit coverage → MVX-002.
- Full nine-year Gmail checkpoints/incremental reconciliation and real OAuth credentials → MVX-003 and MVX-009.
- Live ClamAV/Rspamd and document extraction; attachments currently fail closed → MVX-004.
- Product resolution, duplicate identity merging and complete timelines → MVX-005.
- Calibrated ranking and scheduled digests → MVX-006.
- CRM mapping/delivery; CSV v1 is download-only → MVX-007, MVX-012 and MVX-013.
- Container, PostgreSQL/S3/Redis, backup, restore, rollback, browser and assistive-technology verification → MVX-008.
- Public web enrichment, IMAP and chats → MVX-010, MVX-011 and MVX-015.

### Discovered

The dependency audit found five advisories in two originally selected versions; both dependencies were upgraded before the final audit. The repository began with all process/project files untracked, so there is no prior tracked implementation diff to compare. No real environment or customer data was available or used.

### Decisions

ADRs 0001–0004 record the modular Django architecture, evidence/object storage, local MFA/RBAC, and read-only source/provider contracts. Gmail and all external AI remain disabled by default.

### Assumptions used

A1 defines the eventual one-account Gmail pilot but was not exercised. A2 informs the container shape but remains unverified. A3 informs Turkish/English commercial terms; quality remains unmeasured. U1–U4 remain open and real data is blocked.

### Plan

[MVX-001 plan](plans/MVX-001.md)

### Reviews

[Design review](reviews/MVX-001-design.md) and [ship review](reviews/MVX-001-ship.md). Overall Block for real data; synthetic artifact Pass with conditions and Parked for the two required human approvals. No waiver was granted.
