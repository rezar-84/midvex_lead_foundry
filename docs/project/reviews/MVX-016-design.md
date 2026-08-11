---
status: approved-for-synthetic-build
owner: review-board
last-reviewed: 2026-08-11
---

# Review — MVX-016 project operations and enrichment UI

**Stage:** design **Tier:** 1
**Reviewed:** user request, MVX-016 plan, ADRs 0005–0006, current models/access/pipeline/tasks/UI, security/privacy register and MVX-001 restrictions.

## Verdicts

| Role | Verdict | Checked | Findings and conditions |
| --- | --- | --- | --- |
| product-manager | Pass with conditions | project/source/job/entity/enrichment journey and terminology | S3: extraction quality remains unmeasured; expose candidates and progress, not outcome claims. |
| architect | Pass with conditions | ownership, compatibility migration, adapter and job boundaries | S3: legacy records need nullable project links until backfill. |
| security | Pass with conditions | credentials, rate limits, SSRF, duplicate jobs, egress and audit | S3: network adapters remain feature-gated and tests mock boundaries. |
| qa | Pass with conditions | acceptance criteria and negative matrix | S3: no real-provider contract environment exists. |
| ux-designer | Pass with conditions | first-run project creation, progressive source forms, operations and selection | S3: rendered usability validation remains MVX-008. |
| brand-designer | Pass | reuse of internal tokens and information hierarchy | No new brand claims or assets. |
| copywriter | Pass with conditions | “trained agent,” enrichment, progress and evidence wording | S3: use “extraction profile” unless an evaluated training pipeline exists. |
| accessibility | Pass with conditions | forms, tables, progress semantics, bulk selection and errors | S3: browser/assistive-technology validation remains MVX-008. |
| devops-sre | Pass with conditions | task observability, cancellation, budgets, egress and recovery | S3: live worker/network failure drills are outside synthetic build. |
| privacy-legal | **Block** | credentials, personal-data inference, crawling and retention | **S1:** MVX-009 and U5 are unresolved. Real source/crawler execution is forbidden; synthetic/mocked implementation may proceed. |
| cro-analyst | Pass with conditions | history/quality metrics and batch funnel | S3: quality scores must be labelled heuristic until MVX-006. |

## Outcome

**Overall:** Block for external execution; Pass with conditions for synthetic/mocked implementation.

**Blocking findings:** MVX-009/U2 for real communications and U5/MVX-011 for crawling.

**Waivers:** none.
