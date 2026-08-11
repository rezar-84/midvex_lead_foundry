---
status: draft
owner: product-manager
last-reviewed: 2026-08-11
---

# User stories & acceptance criteria — Midvex Lead Foundry

## Pilot journeys

**MVX-002** — As an administrator, I want individual MFA-protected accounts and scoped roles so access is attributable and least-privilege.

- Given a confirmed MFA device, valid credentials and an active membership, sign-in grants only that role's actions.
- Given a missing/expired/revoked session or membership, every protected route denies access without leaking data.
- A non-admin must not change roles; a non-exporter must not create an export.

**MVX-003** — As an administrator, I want to connect one Gmail account read-only and backfill it safely.

- OAuth requests only `gmail.readonly`; progress is resumable and reruns create no duplicates.
- Revocation stops new work; source errors remain visible and retryable.
- The application must not send, label, delete or otherwise modify Gmail.

**MVX-004** — As an analyst, I want spam and unsafe attachments isolated before analysis.

- Gmail spam labels and local reasoned scores are visible; quarantined messages are excluded by default.
- Unsupported, oversized, suspicious or infected attachments are never executed or passed to AI.
- Reviewer overrides are audited and do not alter source mail.

**MVX-005** — As an analyst, I want evidence-linked contacts, companies, product concepts, interactions and timelines.

- Every derived fact links to a source message and extraction run.
- Ambiguous identity/product merges remain suggestions until confirmed.
- Conflicting or missing facts stay visible; the system must not invent a value.

**MVX-006** — As a reviewer, I want explainable missed-opportunity candidates and in-app digests.

- Every candidate shows the triggering rule, last communication, source evidence, confidence and status.
- Accept/reject/defer decisions are idempotent and audited.
- AI output without valid evidence must not appear as an accepted fact or action.

**MVX-007** — As an exporter, I want a previewed CSV containing only approved records.

- Export shows exact fields and records an immutable manifest before download.
- Unapproved candidates, another organisation's records and quarantined messages are refused.
- Repeating the same export request does not silently create a different payload.
