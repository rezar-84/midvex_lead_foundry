---
status: draft
owner: qa
last-reviewed: 2026-08-11
---

# Test plan — Midvex Lead Foundry

All charter stages run locally and in CI when CI is configured. Tests use synthetic RFC 822 fixtures and mocked external boundaries; production mailbox data is forbidden in tests.

- **Unit:** role policy, project/source forms, TLS/public-address enforcement, spam precedence, MIME limits, identity/direction rules, opportunity rules, evidence validation, budgets and CSV schemas.
- **Integration:** project job constraints, encrypted credential round-trip/non-disclosure, entity metrics/relations, mocked enrichment provenance, object storage, scanners, mocked source pagination/retry and deletion traversal.
- **Contract:** Gmail response fixtures, AI structured schema, Rspamd/ClamAV response parsing, CSV v1.
- **E2E:** MFA sign-in; project creation; synthetic source sync; entity analysis; contact/product/tag views; enrichment selection/review; approved CSV export; denial for wrong role/organisation.
- **Manual:** Turkish/English copy, keyboard/screen-reader/zoom, visual review, labelled opportunity quality and Dokploy rollback.

High-risk cases include permitted/denied/foreign/revoked/tampered access; malformed/oversized/unicode/injection input; forward/reverse migrations; concurrent idempotent jobs; complete purge; provider timeouts and unavailable dependencies.

Known gaps: real OAuth verification, real scanner deployment, browser/assistive matrix, production performance and backup restore remain MVX-008/MVX-009 release gates, not implied coverage.
