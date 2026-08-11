---
status: draft
owner: devops-sre
last-reviewed: 2026-08-11
---

# Release runbook — Midvex Lead Foundry

Build immutable containers from an approved commit. Dokploy supplies environment-specific secrets. Before deploy: all checks, two human approvals, current verified restore, migration reverse test, configuration validation and no open S0–S2.

Procedure: back up PostgreSQL/object storage; deploy additive migrations; deploy web/workers/scheduler/scanners; run checks; enable only synthetic sources; observe health/queue/errors; separately authorise a real mailbox only after MVX-009 is unblocked.

Smoke checks: health/readiness; MFA sign-in and denial; synthetic message ingestion; quarantine; evidence-linked candidate review; CSV export; audit record; no content in logs.

Rollback: pause workers/sources, deploy prior image, reverse only verified migrations, restore data only when integrity requires it, rotate credentials if exposure is suspected, and record the action. Last executed: never — MVX-008 blocks production until staging execution is recorded.
