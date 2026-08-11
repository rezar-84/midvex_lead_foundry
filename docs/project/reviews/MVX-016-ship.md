---
status: approved
owner: review-board
last-reviewed: 2026-08-12
---

# Review — MVX-016 project operations and enrichment UI

**Stage:** ship **Tier:** 1
**Reviewed:** changes after commit `3b28565` on `feat/MVX-016-project-operations-ui`; migrations 0003–0004; project/source/job/taxonomy/metric models; forms, routes, task/services and adapter boundaries; 15 new templates/static assets; tests and check outputs. Real providers, crawler egress, PostgreSQL/Redis/S3, Dokploy and browser assistive technologies were not exercised.

## Verdicts

| Role | Verdict | Checked | Findings and conditions |
| --- | --- | --- | --- |
| product-manager | Pass with conditions | project creation, source onboarding, automatic synthetic sync, batches, entity/history views, tags/products and enrichment review | S3: the quality score is correctly labelled `heuristic-v1`; calibration/digests remain MVX-006. |
| architect | Pass with conditions | project/organisation ownership, additive migrations, active-job constraint, connector and enrichment contracts | S3: full Gmail history reconciliation and live IMAP/POP behavior remain MVX-003/MVX-010. |
| security | Pass with conditions | encrypted credentials, non-disclosure, TLS/standard ports, public-address checks, rate pacing, feature gates, allowlists, egress-proxy requirement, robots/byte/redirect budgets, CSRF/RBAC and audit | S3: real network controls are unverified; they remain disabled. Bandit returned no findings and pip-audit returned no known vulnerabilities. |
| qa | Pass with conditions | 18 tests including role denial, TLS, encryption, SSRF, policy blocks, synthetic project journey, mocked provenance and review | S3: real-provider contract, concurrent-worker, retry and browser matrices remain MVX-003/MVX-008/MVX-010. |
| ux-designer | Pass with conditions | first-run project form, progressive source fields, disabled states, job progress, bulk selection, entities and candidate review in template source | S3: no rendered usability session was run; MVX-008. |
| brand-designer | Pass | reuse of existing visual tokens, cards, tables, status and responsive patterns | No unsupported assets or brand claims introduced. |
| copywriter | Pass | project/source safety language, status/error labels, “heuristic” and “extraction profile” terminology | No claim of autonomous training or guaranteed enrichment quality. |
| accessibility | Pass with conditions | semantic forms/fieldsets/tables/progress, explicit checkbox labels, keyboard-native controls, status text and static checker | S3: 25 templates passed static checks, not WCAG/browser/AT conformance; MVX-008. |
| devops-sre | Pass with conditions | persisted jobs/counters/errors, eager local execution, Celery task boundary, feature flags, egress configuration and rollback docs | S3: asynchronous workers, provider outages and egress proxy were not exercised; MVX-008. |
| privacy-legal | **Block** | project purpose/retention, credentials, communication inference, enrichment provenance and crawler scope | **S1:** U2/MVX-009 and U5/MVX-011 remain unresolved. Real mailbox and crawler execution are forbidden. |
| cro-analyst | Pass with conditions | contact frequency/topics/outcome/sentiment/quality, role/product relations and enrichment selection | S3: metrics are deterministic heuristics without an authorised labelled baseline; MVX-006. |

## Outcome

**Overall:** Block for external execution; Pass with conditions for the synthetic increment, which is Parked pending two human approvals before merge.

**Blocking findings:** U2/MVX-009 blocks real communications; U5/MVX-011 blocks live enrichment; two named Tier 1 approvers remain unknown.

**Waivers:** none.

## Human approvals

| Approval | Named approver | Decision | Date |
| --- | --- | --- | --- |
| Tier 1 approver (solo-operator model, ADR 0007) | Rezar86 (accountable human and data/domain owner) | approved — synthetic increment only; real-source and enrichment authority remain blocked (U2/MVX-009, U5/MVX-011) | 2026-08-12 |
| Tier 1 approver 2 | waived under ADR 0007 until a second maintainer exists; real-data items still require an independent second approver | waived | 2026-08-12 |

This approval does not touch the privacy-legal Block on external execution: real
mailbox and crawler execution remain forbidden until MVX-009/MVX-011 are separately
approved.
