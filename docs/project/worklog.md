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

## MVX-018 — job lifecycle: transaction fix, live progress, cancellation, pagination

**Date:** 2026-08-12 **Tier:** 2
**Status:** Done
**Branch/commits:** `feat/MVX-018-job-progress-and-cancel`, merged to `main` with `--no-ff`

### What changed

Batch jobs are now observable and stoppable. The whole-run `@transaction.atomic`
around `execute_analysis_job` is gone: each message commits in its own savepoint, so
progress counters and partial results are visible while the job runs and survive a
mid-run failure; the contact-metric rollup keeps a single atomic block of its own.
All three executors check for cooperative cancellation (queued jobs are skipped
outright; running jobs stop at a checkpoint every 10 messages, or per item for
enrichment). New `job_cancel` POST view (capability `run_batches`) flips only
queued/running jobs to `CANCELLED` via a conditional update, and a cancel button
appears on the job detail page and jobs table. New `job_status` JSON endpoint plus a
~45-line vanilla `job-progress.js` poll every 2.5 s and reload once the job reaches a
terminal state; the "Refresh this page" copy moved into `<noscript>`. Jobs list and
job-detail items paginate through a new shared `foundry/pagination.py` helper and
`includes/pagination.html` (replacing the silent `[:100]` items slice with a page plus
a real total). The membership context processor now also exposes the role's
capability set to templates, so gating uses capabilities instead of role names.

### Why

The progress UI was lying twice: the analysis job's outer transaction made per-message
progress writes invisible until commit, and the failure-path status write sat inside
the possibly-broken transaction. Fixing that was a precondition for any live progress
display. Vanilla JS was chosen over htmx: one polling surface, zero build step, one
existing JS file as precedent — a dependency was not justified.

### Verified

```
uv run ruff format --check .   → 39 files already formatted
uv run ruff check .            → All checks passed!
uv run mypy foundry lead_foundry → Success: no issues found in 30 source files
uv run pytest -m 'not integration and not contract and not e2e' → 20 passed
uv run pytest -m integration   → 2 passed
uv run pytest -m contract      → 1 passed
uv build                       → wheel + sdist built
uv run bandit -q -r foundry lead_foundry → no findings
uv run pip-audit               → no known vulnerabilities
uv run python scripts/check_a11y.py → 26 templates passed
uv run pytest -m e2e           → 2 passed
uv run python manage.py check / makemigrations --check → clean, no schema drift
```

- [x] `checks.format` — Verified — 39 files formatted
- [x] `checks.lint` — Verified — clean
- [x] `checks.typecheck` — Verified — clean, 30 files
- [x] `checks.unit` — Verified — 20 passed (7 new in `tests/test_job_lifecycle.py`)
- [x] `checks.integration` — Verified — 2 passed
- [x] `checks.contract` — Verified — 1 passed
- [x] `checks.build` — Verified — sdist + wheel
- [x] `checks.scan` — Verified — Bandit and pip-audit clean
- [x] `checks.a11y` — Verified — 26 templates, static checks only
- [x] `checks.e2e` — Verified — 2 passed
- [ ] manual — **Not run** — no rendered browser session; polling and cancel are
  covered by view tests and the JSON contract test, but the JS itself executed in no
  browser. Browser verification remains MVX-008.

### Not done

- The JS poller is untested in a real browser (no browser matrix in this repo) → MVX-008.
- Cancellation under a genuinely asynchronous worker is untested — local runs are
  eager, so the cooperative checkpoint path is exercised only synthetically → MVX-008.
- `_project_contacts` still materialises a list (pagination for contacts lands with
  MVX-019).

### Discovered

- Intended behaviour change, asserted in tests: partial entities from a failed
  analysis run now persist (jobs are PARTIAL-aware); previously the outer transaction
  rolled everything back including the failure status itself.
- `BatchJob.rate_limit_remaining` is written once at sync start and rendered nowhere
  on the job detail page — left for MVX-021's vestigial-field review.

### Decisions

- Vanilla `fetch` poller over htmx (no new dependency for one surface) — recorded
  here, no ADR: reversible in an afternoon.
- Cancellation is cooperative-only; no worker kill. A running worker stops at its
  next checkpoint. Queued jobs cancel immediately because executors check status
  before starting.

### Assumptions used

- AR1 (single-approver) — this Tier 2 item needs no merge approval beyond review.

### Plan

Tier 2 plan (inline): fix the analysis transaction scope first, then add the cancel
path (model already had the status), then the JSON endpoint + poller, then pagination
— each step testable alone. Rejected: htmx (dependency not earned); meta-refresh
(loses scroll position and hammers full page renders); killing workers via revoke
(Celery revoke is unreliable with eager mode and prefetching).

### Reviews

- architect — Pass — savepoint-per-message keeps writes bounded; `_write_contact_metrics`
  stays atomic as one rollup unit; conditional-update cancel avoids the race between a
  cancel POST and `_finish` (the last writer is the worker, which re-reads status at
  checkpoints); pagination helper clamps rather than 500s.
- security — Pass with conditions — S3: `job_status`/`job_cancel` carry the same
  `login+capability+org-scope` decorators as existing job views; foreign-org requests
  404 (tested); cancel is POST+CSRF. Condition: when real async workers arrive
  (MVX-008), re-review checkpoint frequency as a DoS surface.
- qa — Pass — failure persistence, cancel happy/terminal/denied/foreign-org, JSON
  contract and pagination clamp all covered; noted the JS itself is unexecuted (Not
  done).
- ux-designer — Pass with conditions — S3: live progress, cancel affordance and
  `aria-live` status added; no rendered session was run (MVX-008); table gains an
  Actions column only for roles that can act.
- devops-sre — Pass — cooperative checkpoints keep workers interruptible without
  broker-level revoke; eager-mode caveat documented in the cancel flash message.

## MVX-017 — governance close-out: approvals recorded, MVX-001/MVX-016 merged

**Date:** 2026-08-12 **Tier:** 2
**Status:** Done
**Branch/commits:** `feat/MVX-016-project-operations-ui` (six scoped commits `460e7ac..00124e3`) + `docs/MVX-017-governance-closeout`, merged to `main` with `--no-ff`

### What changed

The repository owner (Rezar86) reviewed the parked state and approved the MVX-001 and
MVX-016 synthetic increments for merge, acting as accountable human. To record that
lawfully within the kit: the charter's accountable-human/approver fields are filled;
ADR 0007 establishes the solo-operator approval model (single approver, human-granted
waiver of the two-approver rule, with revisit triggers); U1 is resolved and the waiver
is logged as accepted risk AR1; AGENTS §9 overrides (domain rules, forbidden shortcuts,
approval surface) are written; both ship reviews carry the recorded approval; the
backlog moves MVX-001/MVX-016 to Done and registers MVX-017–MVX-023. The previously
uncommitted MVX-016 worktree was committed as five scoped `feat/test/docs(MVX-016)`
commits plus one `chore(MVX-017)` commit for the agent tooling (`CLAUDE.md`,
`.claude/commands/`).

### Why

Everything downstream (MVX-018+) must build on committed, approved work; the SDLC
forbids stacking on a parked Tier 1 branch. The two-approver rule cannot be satisfied
by a one-person project; the alternative — parking all Tier 1 work indefinitely — kills
the pilot. A named human granting a recorded, bounded waiver is the kit-compatible
resolution; an agent could not have made this decision.

### Verified

Full chain re-run on the committed tree (the MVX-016 worklog claims were made against
the uncommitted worktree):

```
uv run ruff format --check .   → 37 files already formatted
uv run ruff check .            → All checks passed!
uv run mypy foundry lead_foundry → Success: no issues found in 29 source files
uv run pytest -m 'not integration and not contract and not e2e' → 13 passed
uv run pytest -m integration   → 2 passed
uv run pytest -m contract      → 1 passed
uv build                       → wheel + sdist built
uv run bandit -q -r foundry lead_foundry → no findings
uv run pip-audit               → no known vulnerabilities (local package unauditable, expected)
uv run python scripts/check_a11y.py → 25 templates passed
uv run pytest -m e2e           → 2 passed
uv run python manage.py check  → no issues; makemigrations --check → no changes
```

- [x] `checks.format` — Verified — 37 files already formatted
- [x] `checks.lint` — Verified — all checks passed
- [x] `checks.typecheck` — Verified — clean, 29 files
- [x] `checks.unit` — Verified — 13 passed
- [x] `checks.integration` — Verified — 2 passed
- [x] `checks.contract` — Verified — 1 passed
- [x] `checks.build` — Verified — sdist + wheel
- [x] `checks.scan` — Verified — Bandit no findings; pip-audit clean
- [x] `checks.a11y` — Verified — 25 templates, static checks only
- [x] `checks.e2e` — Verified — 2 passed
- [x] manual — reviewed diff of every governance edit before commit

### Not done

- Browser/AT accessibility conformance, async workers, real providers — unchanged, still → MVX-008/MVX-003/MVX-010.
- ADRs 0001–0004 still say `Status: Proposed` in an older front-matter format → cleanup folded into MVX-021.
- Legacy nullable project-link backfill (ADR 0005 condition) has no backlog ID yet → to be registered when MVX-022 is planned.

### Discovered

- The MVX-001 worklog entry's "Branch/commits: … uncommitted" note was stale — commit
  `3b28565` existed. Correction: MVX-001's code was committed on 2026-08-11; only
  MVX-016's increment was uncommitted until today.
- `.gitignore` already covered `db.sqlite3`/`.env`; nothing sensitive was at risk of
  being committed.

### Decisions

- ADR 0007 — solo-operator approval model (single named approver with recorded waiver;
  independent second approver still required for real-data items).
- Backlog IDs MVX-017–MVX-021 assigned to the continuation sequence (job lifecycle,
  UI consistency, white-label configuration, configuration truth); MVX-022/MVX-023
  registered as deferred.

### Assumptions used

- A2 (Dokploy shape) untouched. AR1 (single-approver risk) newly accepted — if wrong
  (i.e. a second reviewer would have caught something), the exposure is bounded to
  synthetic-data increments.

### Plan

Tier 2, so the plan lives here: commit the MVX-016 worktree as scoped commits on its
feature branch; re-run the full chain against the committed tree; make the governance
edits on `docs/MVX-017-governance-closeout` (charter, ADR 0007, AGENTS §9, U1→AR1,
ship-review approval tables, plan/backlog statuses, this entry); merge to `main` with
`--no-ff`. Rejected alternative: recording two approvers by naming the agent as one —
forbidden, an agent is not an approver. Rejected: leaving the work unmerged and
building on the parked branch — forbidden by the loop's stopping rule.

### Reviews

- product-manager — Pass — checked traceability of the approval chain (charter → ADR
  0007 → AR1 → ship reviews → backlog); IDs and statuses consistent across all six
  documents.
- architect — Pass — checked that the commit split preserves reviewable boundaries
  (models/migrations+services, views/urls, templates/static, tests, docs) and that no
  code changed during the close-out; `git diff 3b28565..HEAD -- foundry/` matches the
  reviewed MVX-016 diff.

## MVX-016 — project operations and enrichment UI

**Date:** 2026-08-11 **Tier:** 1
**Status:** Parked
**Branch/commits:** `feat/MVX-016-project-operations-ui` / uncommitted; merge requires two named human approvals

### What changed

Added an organisation-scoped product UI for creating projects, configuring synthetic,
Gmail, IMAP and POP3 lead sources, viewing synchronisation and analysis jobs, exploring
contacts and products, assigning tags, reviewing interaction metrics and relations, and
running contact enrichment batches. Added persisted job/entity/provenance models,
read-only rate-paced source adapters, public-web enrichment controls, extraction-profile
versioning, migrations, synthetic demo data and tests. Real network execution remains
disabled by global and project gates.

### Why

Operators need one understandable workflow from source onboarding through reviewed
knowledge and enrichment. Persisted project-scoped jobs make progress and failure
visible, while explicit network gates, allowlists, provenance and human review prevent
an attractive UI from silently authorising processing of personal communications or
unapproved crawling.

### Verified

- [x] `checks.format` — **Verified** — `ruff format --check .`: 37 files already formatted.
- [x] `checks.lint` — **Verified** — `ruff check .`: all checks passed; Ruff emitted its Python 3.14 preview warning.
- [x] `checks.typecheck` — **Verified** — mypy found no issues in 29 source files.
- [x] `checks.unit` — **Verified** — 15 passed, 3 deselected.
- [x] `checks.integration` — **Verified** — 2 passed, 16 deselected.
- [x] `checks.contract` — **Verified** — 1 passed, 17 deselected.
- [x] `checks.build` — **Verified** — source distribution and wheel built successfully.
- [x] `checks.scan` — **Verified** — Bandit completed with no findings; pip-audit reported no known vulnerabilities and skipped the private package because it is not on PyPI.
- [x] `checks.a11y` — **Verified** — static checks passed for 25 templates.
- [x] `checks.e2e` — **Verified** — 2 passed, 16 deselected; the synthetic project journey covered sync, analysis, entity display, tagging and mocked enrichment review.
- [x] manual — **Verified** — Django system check reported no issues; migration dry-run reported no changes; local migrations and `seed_demo` completed successfully. No real provider, crawler, production environment, browser or assistive technology was exercised.

### Not done

- Real Gmail authority, full-history checkpoints and reconciliation → MVX-003 and MVX-009.
- Live IMAP/POP provider matrices and chat sources → MVX-010 and MVX-015.
- Legal basis, source approval and production egress for live enrichment → MVX-011 and U5.
- Live message/attachment scanning → MVX-004.
- Entity deduplication, calibrated scoring and digests → MVX-005 and MVX-006.
- Production asynchronous workers, browser/assistive-technology tests, backup/restore and deployment verification → MVX-008.
- Autonomous crawler training is not implemented; extraction behaviour is explicitly versioned through reviewable extraction profiles → new scope requires its own approved work item.

### Discovered

Configuration screens alone are insufficient evidence that external providers are safe
or authorised. Gmail, IMAP, POP3 and live web enrichment therefore remain visible but
disabled. Contact quality and sentiment are deterministic `heuristic-v1` outputs, not
validated predictions. No customer data or real credentials were used.

### Decisions

[ADR 0005](adr/0005-project-scoped-operations-and-jobs.md) records project-scoped
persisted operations. [ADR 0006](adr/0006-gated-enrichment-service.md) records the
gated, provenance-preserving enrichment boundary. Existing ADRs continue to govern
evidence, identity, authentication and read-only provider access.

### Assumptions used

A1–A3 shape the eventual Gmail-first, containerised, bilingual workflow but were not
validated by this synthetic increment. U2 and U5 remain unresolved; if authority or
lawful enrichment scope differs, the external-source and crawler designs must change.

### Plan

[MVX-016 plan](plans/MVX-016.md)

### Reviews

[Design review](reviews/MVX-016-design.md) and [ship review](reviews/MVX-016-ship.md).
Privacy/legal returns Block for real external execution. The synthetic increment is
Pass with conditions and Parked pending two named human approvals; no waiver was granted.

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
