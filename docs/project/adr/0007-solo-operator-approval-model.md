---
status: accepted
owner: Rezar86
last-reviewed: 2026-08-12
---

# ADR 0007 — Solo-operator approval model

## Context

`docs/process/05-change-control.md` requires two named human approvers for a Tier 1 merge, and an agent counts as neither. The charter's accountable-human and approver fields were unfilled (open unknown U1), which parked MVX-001 and MVX-016 indefinitely. The project currently has exactly one human: the repository owner, who is also the data/domain owner of the synthetic pilot.

## Decision

Rezar86 (paraxweb@gmail.com) is recorded as the accountable human and the sole named Tier 1 approver. The two-approver requirement is waived by that human — a human-granted policy waiver, not an agent decision — for as long as the project has a single maintainer. The waiver is recorded as an accepted risk in `assumptions-and-risks.md` and must be revisited when either trigger fires: a second maintainer joins, or MVX-009 (real mailbox connection) opens. Real-data authorisation explicitly requires an independent second approver; this waiver does not extend to it.

## Consequences

Tier 1 items can merge on one recorded human approval, unblocking MVX-001/MVX-016 and the continuation sequence. Single-approver review concentrates risk in one person; the compensating controls are the unchanged role-review record, the full check chain per merge, and the synthetic-only scope. The privacy-legal Block on external execution (real sources, real enrichment egress) stands and is not waivable under this ADR.

## Rollback

Restore the two-approver requirement by superseding this ADR; re-park any item whose only approval was granted under it if its risk posture changed.
