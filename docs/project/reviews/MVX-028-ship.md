---
status: approved
owner: review-board
last-reviewed: 2026-08-12
---

# Review — MVX-028 editable instance settings

**Stage:** ship **Tier:** 1
**Reviewed:** full diff on `feat/MVX-028-editable-instance-settings`: model +
migration 0005, `runtime_settings.py`, consumer wiring, POST endpoint, template,
6-assertion test. No real Google credentials exercised.

| Role | Verdict | Findings |
| --- | --- | --- |
| security | Pass | ciphertext-at-rest, never-rendered, gate-refusal and 403 all asserted in tests; audit event on every change; whitelist is the single authority. |
| architect | Pass | consumers read through one resolver; env fallback keeps rollback trivial. |
| qa | Pass | 42 passed; migration additive/reversible. |
| privacy-legal | Pass | standing Block on external execution unaffected; gates not editable (tested). |
| devops-sre / ux-designer / others | Pass | clearing restores env value; no redeploy needed for key rotation. |

**Overall:** Pass. **Waivers:** none.

| Approval | Named approver | Decision | Date |
| --- | --- | --- | --- |
| Tier 1 approver (ADR 0007) | Rezar86 | approved | 2026-08-12 |
