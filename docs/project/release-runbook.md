---
status: draft
owner: devops-sre
last-reviewed: 2026-08-11
---

# Release runbook — Midvex Lead Foundry

Build immutable containers from an approved commit. Dokploy supplies environment-specific secrets. Before deploy: all checks, two human approvals, current verified restore, migration reverse test, configuration validation and no open S0–S2.

Procedure: back up PostgreSQL/object storage; deploy additive migrations; deploy web/workers/scheduler/scanners; run checks; enable only synthetic sources; observe health/queue/errors. Keep `SOURCE_NETWORK_ENABLED`, `GMAIL_REAL_DATA_ENABLED` and `ENRICHMENT_NETWORK_ENABLED` false. A real mailbox requires MVX-009 approval; enrichment additionally requires U5/MVX-011 approval and a verified `ENRICHMENT_EGRESS_PROXY`.

Smoke checks: health/readiness; MFA sign-in and denial; project creation; synthetic source sync; job progress; entity analysis; contact/product/tag history; policy-blocked external source/enrichment; evidence-linked candidate review; CSV export; audit record; no credentials/content in logs.

Rollback: pause workers/sources, deploy prior image, reverse only verified migrations, restore data only when integrity requires it, rotate credentials if exposure is suspected, and record the action. Last executed: never — MVX-008 blocks production until staging execution is recorded.
