---
status: approved
owner: review-board
last-reviewed: 2026-08-12
---

# Review — MVX-025 production deployment readiness

**Stage:** ship **Tier:** 1
**Reviewed:** the diff on `feat/MVX-025-production-deployment-readiness`:
entrypoint script, compose changes, `.env.production.example`, README Dokploy
walkthrough, ADR 0009. No Python code changed. No real Dokploy deploy was
executed — first deploy follows the release runbook.

## Verdicts

| Role | Verdict | Checked | Findings and conditions |
| --- | --- | --- | --- |
| architect | Pass | migrate-in-web-entrypoint only; worker untouched; single-replica assumption in ADR 0009 | Design condition met. |
| security | Pass with conditions | template has placeholder secrets only; all three gates false; Fernet-loss warning present; `.env` remains gitignored | S3: first-deploy secrets must be generated fresh, never copied from any example or chat. |
| qa | Pass | full chain green (40 tests, no Python delta); `sh -n` clean; `docker compose config` valid with template env; compose refuses missing `POSTGRES_PASSWORD` | Runbook smoke list governs the live deploy — not claimed here. |
| devops-sre | Pass with conditions | healthcheck via in-image Python; restart policies on all services; `evidence_data` volume on web+worker; postgres-healthy dependency for worker | S3: backup/restore of `postgres_data`+`evidence_data` is documented but **undrilled** — remains MVX-008 and blocks calling this production-proven. |
| privacy-legal | Pass | synthetic-only build; gates false; no new data category | The standing Block on real-source/enrichment execution (U2/MVX-009, U5/MVX-011) is unaffected and remains. |
| product-manager / ux-designer / brand-designer / copywriter / accessibility / cro-analyst | Pass | README walkthrough accuracy, brand env values for the Midvex instance | No UI change. |

## Outcome

**Overall:** Pass with conditions — approved to merge; the deployment itself must
follow `release-runbook.md` (smoke list, backups) and MVX-008 remains open for
backup/restore/rollback drills.

**Waivers:** none.

## Human approvals

| Approval | Named approver | Decision | Date |
| --- | --- | --- | --- |
| Tier 1 approver (solo-operator model, ADR 0007) | Rezar86 | approved — deployment preparation; production go-live per runbook; network gates stay false | 2026-08-12 |

## Addendum — MVX-026 staging drill (same day)

Executing the runbook smoke list against a local production-mode stack exposed two
defects in the reviewed increment, both fixed under this item's approval:
(1) `uv run` at runtime failed as the non-root user (build cache unwritable) —
runtime now uses the venv directly via `PATH`, no `uv` after build; (2) the
`evidence_data` volume was root-owned so the app could not write evidence (the
`PermissionError` surfaced misleadingly as `NETWORK_POLICY_BLOCK`), and the
healthcheck followed the HTTPS redirect and failed — the image now creates
`/data/evidence` owned by the app user, and the healthcheck sends
`X-Forwarded-Proto`. Re-review (architect, security, devops-sre): Pass — fixes are
contained to the container layer; no Python change.
