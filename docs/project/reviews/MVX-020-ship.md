---
status: approved
owner: review-board
last-reviewed: 2026-08-12
---

# Review — MVX-020 white-label configuration and provisioning

**Stage:** ship **Tier:** 1
**Reviewed:** the full diff on `feat/MVX-020-white-label-configuration`: settings
(brand/user-agent/locale), `foundry/heuristics.py`, profile wiring through
sync/analysis/enrichment, neutralised synthetic fixtures, `seed_demo` parameters,
`provision` command, template/context brand consumption, docs and 7 new tests. No
real providers, browsers or async workers were exercised.

## Verdicts

| Role | Verdict | Checked | Findings and conditions |
| --- | --- | --- | --- |
| product-manager | Pass | provisioning journey (command → sign-in → MFA), README self-hosting section, follow-up registration | Profile editor UI recorded as follow-up in backlog notes; scope delivered as planned. |
| architect | Pass | fallback semantics (highest-version row wins, absence = defaults), `lru_cache` on `default_profile`, pipeline's optional profile parameter, removal of duplicated pattern constants | Design condition met: parity test (`test_default_profile_reproduces_current_extraction`) locks default behaviour. Single compile per job run; no per-message compilation. |
| security | Pass with conditions | `_compile` validation (type, 500-char cap, 32-entry group cap, `re.error` handling), `provision` credential path (env or `getpass`, never echoed, never resets existing passwords), user-agent disclosure string | Design conditions met and tested (`test_invalid_field_rules_are_rejected`, `test_provision_is_idempotent_and_never_echoes_password`). S3: Python's `re` has no global timeout; caps reduce but do not eliminate pathological patterns — acceptable while profile rows are admin-authored; revisit if a profile editor UI (follow-up) opens authorship wider. |
| qa | Pass | 39 total tests; parity, override, invalid-rules, fallback-merge, idempotency, brand/TOTP rendering; full chain output | All ten stages verified; seed_demo smoke run recorded. |
| ux-designer | Pass with conditions | brand rendering in header/title, provisioning command ergonomics | S3: no rendered session (MVX-008), unchanged condition. |
| brand-designer | Pass | neutral default brand, removal of MIDVEX header mark | Brand becomes deployment identity; no residual Midvex marks in runtime surfaces. |
| copywriter | Pass | README self-hosting copy, fixture scenario copy, command help text | "White-label", "extraction profile" terminology consistent with ADR 0006's learning language. |
| accessibility | Pass | brand text substitution, no new interactive surfaces | Static checks pass for 27 templates. |
| devops-sre | Pass | `.env.example` completeness, rollback (unset vars, delete rows), no migration, `LocaleMiddleware` order | Rollback requires no data operation; middleware ordering verified against session/common placement. |
| privacy-legal | **Block** (external execution) / Pass for this increment | fixture neutrality (`demo-seller.test`), user-agent contact string ("instance operator", no person named), provisioning stores only username/email | The standing S1 Block on real-source and enrichment execution (U2/MVX-009, U5/MVX-011) is untouched by this item and remains. Nothing in this increment enables network execution. |
| cro-analyst | Pass | metric semantics unchanged, `extraction_profile_version` now truthful in enrichment records | Calibration remains MVX-006. |

## Outcome

**Overall:** Pass with conditions for the synthetic increment; the standing
privacy-legal Block on external execution remains and is not weakened. Conditions
(parity test, validation caps, secret hygiene, env documentation) are all met in
the diff.

**Waivers:** none.

## Human approvals

| Approval | Named approver | Decision | Date |
| --- | --- | --- | --- |
| Tier 1 approver (solo-operator model, ADR 0007) | Rezar86 | approved — synthetic increment; real-source and enrichment authority remain blocked | 2026-08-12 |
