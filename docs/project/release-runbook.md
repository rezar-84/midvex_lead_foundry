---
status: draft
owner: devops-sre
last-reviewed: 2026-08-11
---

# Release runbook — Midvex Lead Foundry

Build immutable containers from an approved commit. Dokploy supplies environment-specific secrets. Before deploy: all checks, two human approvals, current verified restore, migration reverse test, configuration validation and no open S0–S2.

Procedure: back up PostgreSQL/object storage; deploy additive migrations; deploy web/workers/scheduler/scanners; run checks; enable only synthetic sources; observe health/queue/errors. Keep `SOURCE_NETWORK_ENABLED`, `GMAIL_REAL_DATA_ENABLED` and `ENRICHMENT_NETWORK_ENABLED` false. A real mailbox requires MVX-009 approval; enrichment additionally requires U5/MVX-011 approval and a verified `ENRICHMENT_EGRESS_PROXY`.

Smoke checks: health/readiness; MFA sign-in and denial; SPA shell loads on an unknown path and `/api/me` returns the membership JSON (401 JSON when signed out); hashed `/static/assets/*` bundle serves with immutable cache headers; project creation; synthetic source sync; job progress polling; entity analysis (and auto-digest chaining when enabled); dedup run + merge-suggestion review; contact/product/tag history; policy-blocked external source/enrichment; evidence-linked candidate review; CSV export; audit record; no credentials/content in logs. After the MVX-032 OAuth move, confirm `GOOGLE_REDIRECT_URI` is `https://mlf.midvex.com/integrations/gmail/callback/` in both Dokploy env and the Google console before exercising the connect flow.

Rollback: pause workers/sources, deploy prior image, reverse only verified migrations, restore data only when integrity requires it, rotate credentials if exposure is suspected, and record the action.

Last executed: 2026-08-12 (MVX-026) — smoke list and a full backup → destroy →
restore drill of `postgres_data` + `evidence_data` ran against a local
production-mode compose stack (DEBUG false, real Celery worker): health, HTTPS
redirect, hashed static serving, provision, synthetic sync/analysis, an
asynchronous worker job, evidence writes, policy gates false; post-restore counts
and evidence SHA-256 hashes identical, `migrate --check` consistent. The same
drill on the Dokploy host itself remains open under MVX-008.
