---
status: approved
owner: review-board
last-reviewed: 2026-08-12
---

# Review — MVX-020 white-label configuration and provisioning

**Stage:** design **Tier:** 1
**Reviewed:** `docs/project/plans/MVX-020.md` against the MVX-019 codebase.

## Verdicts

| Role | Verdict | Checked | Findings and conditions |
| --- | --- | --- | --- |
| product-manager | Pass | white-label scope vs MVX-014 boundary, provisioning UX, profile-editor deferral | Single-tenant scope is explicit; the profile editor UI is a named follow-up, not an implied feature. |
| architect | Pass with conditions | fallback-instead-of-seeding decision, profile compile path, package-name-vs-brand split | S3: the fallback design must be locked by a parity test so default behaviour cannot drift silently — condition carried to ship review. |
| security | Pass with conditions | regex-from-data (ReDoS), provisioning credential path, user-agent disclosure | S3: `field_rules` must be length/count-capped and compile-validated before use; `provision` must never echo or log the password. Conditions carried to ship review. |
| qa | Pass | parity/override/invalid-rules/idempotency test plan | Negative cases named in the plan match the Tier 1 requirement. |
| ux-designer | Pass | provisioning flow (CLI), brand rendering surfaces | CLI-first provisioning is acceptable for the self-hosted operator persona; no rendered session required at design stage. |
| brand-designer | Pass | brand token surfaces (header, title, TOTP issuer, user-agent) | Defaults are neutral ("Lead Foundry"); no third-party brand assets introduced. |
| copywriter | Pass | README self-hosting copy plan, neutral fixture scenario | Fixture scenario stays on reserved `.test` domains; no real-company implication. |
| accessibility | Pass | no new interactive surfaces | Brand text substitution only. |
| devops-sre | Pass | env-var surface, rollback (unset vars), no migration | Rollback is trivial by design; `.env.example` must document every new variable. |
| privacy-legal | Pass with conditions | fixture neutrality, user-agent contact string, provisioning data | S3: the user-agent default must not name a person; enrichment/network gates are untouched by this item. The standing Block on external execution (U2/U5) is unaffected and remains. |
| cro-analyst | Pass | extraction parity requirement | Metric semantics (`heuristic-v1`) unchanged; profile versions become visible in enrichment records. |

## Outcome

**Overall:** Pass with conditions — approved for synthetic build. Conditions: parity
test locks default behaviour; field-rule validation with caps; no secret echo in
provisioning; `.env.example` documents all new variables.

**Waivers:** none. The privacy-legal Block on external execution stands and is out
of scope here.

## Human approvals

| Approval | Named approver | Decision | Date |
| --- | --- | --- | --- |
| Tier 1 approver (solo-operator model, ADR 0007) | Rezar86 | approved — design for synthetic build | 2026-08-12 |
