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

## MVX-021 — configuration truth and dead-code labelling

**Date:** 2026-08-12 **Tier:** 2
**Status:** Done
**Branch/commits:** `chore/MVX-021-config-cleanup`, merged to `main` with `--no-ff`

### What changed

Settings now promise only what exists. `MAX_MESSAGE_BYTES` is actually enforced
(`pipeline.ingest_rfc822` read a hardcoded 25 MB before). The unread
`RSPAMD_URL`/`CLAMAV_*`, `MAX_ATTACHMENT_BYTES` and the whole `AI_*` block are
deleted from settings and `.env.example` — there is no LLM call in this codebase
and no scanner client; MVX-004/MVX-006 reintroduce those settings together with
real consumers. The orphaned `sync_gmail` Celery task (no caller since the
project-scoped sync path replaced it) is removed; MVX-003 will reintroduce a
checkpointed variant. The reserved models (`ModelRun`, `Digest`,
`ResearchArtifact`) and vestigial fields (`BatchJob.configuration`,
`rate_limit_remaining`, `ProjectEntity.review_status`) carry docstrings naming
their owning future item, and `data-model-api.md` lists them as reserved —
dropping them is destructive and stays in MVX-022.

### Why

Dead configuration reads as capability: an operator seeing `AI_API_KEY` and
`CLAMAV_HOST` in `.env.example` would reasonably believe scanning and AI ranking
exist. For a white-label product that is a truthfulness bug, not just clutter.

### Verified

```
uv run ruff format --check . / ruff check . / mypy → all clean (32 source files)
uv run pytest → 40 passed (1 new: oversize rejection driven by the setting)
uv build → wheel + sdist; bandit → no findings; pip-audit → clean
uv run python scripts/check_a11y.py → 27 templates
uv run python manage.py check / makemigrations --check → clean; docstrings add no migration
```

- [x] `checks.format` — Verified · [x] `checks.lint` — Verified · [x] `checks.typecheck` — Verified
- [x] `checks.unit`/`integration`/`contract`/`e2e` — Verified — within 40-passed full run
- [x] `checks.build` — Verified · [x] `checks.scan` — Verified · [x] `checks.a11y` — Verified — static only
- [ ] manual — **Not run** — no browser session needed for this change.

### Not done

- Dropping reserved schema and honouring `retention_days` (purge job) → MVX-022 (Tier 1, data deletion).
- ADRs 0001–0004 still carry `Status: Proposed` in an older front-matter format — left untouched: rewriting decision records requires the accountable human's explicit call; flagged here instead.

### Discovered

- `SECRET_KEY`/`TOKEN_ENCRYPTION_KEY` DEBUG fallbacks already hard-fail when
  `DJANGO_DEBUG=false` (settings.py raises; crypto derives only in DEBUG/TESTING) —
  checked and acceptable for self-hosting; no change needed.
- `BatchJob.configuration` is rendered on the job detail page but never written —
  the display shows an always-empty dict; left as-is and labelled (MVX-010 owns it).

### Decisions

- Delete-and-reintroduce over keep-and-document for unread settings: a setting with
  no consumer cannot be verified, so its presence violates the evidence rules. No
  ADR — reversible trivially.

### Assumptions used

- MVX-004/MVX-006/MVX-010/MVX-011 remain the owning items for the reserved schema;
  if those are dropped, MVX-022 should remove the schema too.

### Plan

Tier 2 plan (inline): wire the one hardcoded limit to its setting with a test;
delete unread settings and scrub `.env.example`; remove the uncalled task; label —
never delete — reserved models. Rejected: dropping the dead tables now (destructive
migration → Tier 1, out of scope).

### Reviews

- architect — Pass — grep-verified no consumer for each deleted setting and no
  caller for `sync_gmail` (`iter_messages` retains its live consumer in
  `connectors.py`); reserved-schema labels point at real backlog items.
- security — Pass — removing unused credential-shaped settings (`AI_API_KEY`)
  shrinks the secret surface; size-limit enforcement now testable and tested.
- devops-sre — Pass — `.env.example` matches settings exactly; no compose services
  referenced the removed endpoints.

## MVX-020 — white-label configuration and provisioning

**Date:** 2026-08-12 **Tier:** 1
**Status:** Done
**Branch/commits:** `feat/MVX-020-white-label-configuration`, merged to `main` with `--no-ff`; approval recorded per ADR 0007

### What changed

The product is now deployable for any organisation. Brand identity comes from
`FOUNDRY_BRAND_NAME` (header, page titles, TOTP issuer) and `FOUNDRY_USER_AGENT`
(enrichment fetcher); locale from `DJANGO_LANGUAGE_CODE`/`DJANGO_LANGUAGES` with
`LocaleMiddleware` enabled. The extraction heuristics moved from compiled constants
in `operations.py`/`pipeline.py` into `foundry/heuristics.py` as
`DEFAULT_FIELD_RULES`, compiled into a validated per-project `CompiledProfile`; the
previously dead `ExtractionProfile` model is now live — a project-scoped row
(entity type `message`, highest version wins) overrides any rule, absence means
shipped defaults, and enrichment records the active profile version. Synthetic
fixtures were neutralised to `demo-seller.test` constants; `seed_demo` gained
`--org-name/--org-slug`; a new idempotent `provision` command creates an
organisation plus first admin without `/admin`. ADR 0008 records the decisions.

### Why

White-label single-tenant reuse was the decided target. The heuristics were the
deepest coupling: regex constants baked a Turkish dental-scanner business into
extraction. Wiring the existing (dead) ExtractionProfile model makes rules a data
override with a shipped default, instead of a fork-the-code customisation.

### Verified

```
uv run ruff format --check .   → 43 files already formatted
uv run ruff check .            → All checks passed!
uv run mypy foundry lead_foundry → Success: no issues found in 32 source files
uv run pytest                  → 39 passed (7 new in tests/test_white_label.py)
uv build                       → wheel + sdist built
uv run bandit -q               → no findings
uv run pip-audit               → no known vulnerabilities
uv run python scripts/check_a11y.py → 27 templates passed
uv run python manage.py check / makemigrations --check → clean; NO new migration
uv run python manage.py seed_demo → "Synthetic demo data created" (smoke, sqlite)
```

- [x] `checks.format` — Verified — 43 files
- [x] `checks.lint` — Verified — clean
- [x] `checks.typecheck` — Verified — clean, 32 files
- [x] `checks.unit` — Verified — within 39-passed full run
- [x] `checks.integration` — Verified — within full run
- [x] `checks.contract` — Verified — within full run
- [x] `checks.build` — Verified — sdist + wheel
- [x] `checks.scan` — Verified — Bandit and pip-audit clean
- [x] `checks.a11y` — Verified — 27 templates, static checks only
- [x] `checks.e2e` — Verified — within full run
- [x] manual — seed_demo + migrate smoke on sqlite; no rendered browser session (MVX-008)

### Not done

- Profile editor UI (create/edit `ExtractionProfile` rows from the product) →
  follow-up; rows are admin/ORM-authored for now.
- `{% trans %}` extraction sweep → MVX-023.
- Many templates still hardcode "· Lead Foundry" in their `{% block title %}`
  suffix; the base default uses the brand but per-page suffixes don't → fold into
  MVX-023's copy sweep.
- Multi-tenant brand/config and web onboarding → MVX-014.

### Discovered

- The planned "seed default profile per project + backfill migration" was dropped:
  with a code fallback, seeded rows duplicating defaults would drift when defaults
  improve and would need their own migration to remove. Deviation recorded in the
  plan and ADR 0008; consequence — this item ships **no migration**.
- `pipeline.py` kept a second copy of the opportunity/exclusion patterns; both
  copies now live once in `DEFAULT_FIELD_RULES`.

### Decisions

- ADR 0008 — configuration-driven white-labelling and data-driven extraction
  profiles (fallback over seeding; CLI provisioning over a web wizard; package name
  is not runtime brand).

### Assumptions used

- Single-deployment/single-brand until MVX-014. AR1 (solo approver) for the merge.

### Plan

`docs/project/plans/MVX-020.md` (approved).

### Reviews

`docs/project/reviews/MVX-020-design.md` (Pass with conditions) and
`docs/project/reviews/MVX-020-ship.md` (Pass with conditions for the synthetic
increment; the standing privacy-legal Block on external execution remains).
Approval recorded per ADR 0007.

## MVX-019 — UI consistency: pagination, unified forms, capability gating, empty states, MFA QR

**Date:** 2026-08-12 **Tier:** 2
**Status:** Done
**Branch/commits:** `feat/MVX-019-ui-consistency`, merged to `main` with `--no-ff`

### What changed

Every list paginates (contacts, products, opportunities, conversations, knowledge —
reusing MVX-018's helper and include, preserving filter querystrings). All eight
`{{ form.as_p }}` sites now render through a shared
`templates/foundry/includes/form_fields.html` include with per-field labels, help
text and inline errors, matching the hand-built source form. Navigation and action
affordances are gated by capability, not role name: the Tags link hides from roles
without `run_batches`; the contacts bulk bar shows tag controls to `run_batches` and
enrichment controls to `run_enrichment` (previously admin-only, which locked analysts
out of a capability they hold); Sources/Settings/Create-project/Export/Review
affordances all read the new `capabilities` context value. Invalid bulk submissions
on the contacts page re-render with field errors and the selection preserved
(HTTP 400) instead of a lossy redirect with a generic flash. Empty lists show
explanatory `.empty-state` panels. The opportunities status filter marks the active
link with `aria-current`. MFA setup shows a QR code (new pinned dependency `segno`,
pure-Python SVG) beside the existing secret. The remaining one-lined templates were
re-wrapped to multi-line.

### Why

Presentation debt concentrated in three patterns — unpaginated querysets, `as_p`
dumps, and role-name gating that disagreed with the capability map — so the fix is
three shared mechanisms (paginate helper, form include, `capabilities` in template
context) applied everywhere, rather than page-by-page patches.

### Verified

```
uv run ruff format --check .   → 40 files already formatted
uv run ruff check .            → All checks passed!
uv run mypy foundry lead_foundry → Success: no issues found in 30 source files
uv run pytest                  → 33 passed (8 new in tests/test_ui_consistency.py)
uv build                       → wheel + sdist built
uv run bandit -q               → no findings
uv run pip-audit               → no known vulnerabilities (segno 1.6.6 audited clean)
uv run python scripts/check_a11y.py → 27 templates passed
uv run python manage.py check / makemigrations --check → clean, no schema drift
```

- [x] `checks.format` — Verified — 40 files
- [x] `checks.lint` — Verified — clean
- [x] `checks.typecheck` — Verified — clean, 30 files
- [x] `checks.unit` — Verified — within the 33-passed full run
- [x] `checks.integration` — Verified — within the full run
- [x] `checks.contract` — Verified — within the full run
- [x] `checks.build` — Verified — sdist + wheel
- [x] `checks.scan` — Verified — Bandit and pip-audit clean, `segno==1.6.6` pinned
- [x] `checks.a11y` — Verified — 27 templates, static checks only
- [x] `checks.e2e` — Verified — within the full run
- [ ] manual — **Not run** — no rendered browser/AT session; MVX-008.

### Not done

- Contacts pagination paginates the materialised list from `_project_contacts`
  (correct, but the queryset-level optimisation is deferred) → noted for MVX-021/022.
- A read-only Tags view for reviewers was rejected for now: it would loosen an
  authorisation check, which is Tier 1 → candidate future item.
- Rendered usability/WCAG conformance still unverified → MVX-008.

### Discovered

- `contact_tag_assign` built its tag choices differently from the page
  (`tag.name` vs `category: name`), invisible before because errors collapsed to a
  flash message; both now share `_tag_choices`.
- The template reflow could not be a separate commit as planned: every long-lined
  template also needed capability-gating edits, so separating reflow from gating
  would have produced two overlapping rewrites of the same lines.

### Decisions

- New dependency `segno` (QR): pure-Python, no image library, SVG output, ~135 kB;
  justified for a material MFA-enrolment usability gap; pinned and audited.
- Form errors return HTTP 400 on re-render so failures are visible to tests and
  monitoring rather than masked by a 302.

### Assumptions used

- Capability map in `foundry/access.py` is the single authority for what each role
  may do; templates now assume it rather than restating role names.

### Plan

Tier 2 plan (inline): build the form include and capability context first, then apply
per template; pagination reuses MVX-018's helper; contacts form fixed by
render-on-error with preserved selection rather than splitting into two forms (the
checkbox set is shared state — two forms would duplicate the table or lose
selection). Rejected: JS-based selection persistence (server render is simpler and
works without JS).

### Reviews

- ux-designer — Pass with conditions — S3: affordances now match capabilities;
  selection loss on error fixed; no rendered session run (MVX-008).
- accessibility — Pass with conditions — S3: `aria-current` on filters, labelled
  QR image, field errors adjacent to inputs, `role="alert"` on the form-error
  summary; static checks only, conformance remains MVX-008.
- copywriter — Pass — empty states explain the next action in product voice; no new
  capability or accuracy claims introduced.
- qa — Pass — nav gating per role, error re-render with preserved selection,
  pagination bounds, QR render and empty states covered by 8 new tests; noted the
  admin e2e journey still passes unchanged.

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
