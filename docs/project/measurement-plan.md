---
status: draft
owner: cro-analyst
last-reviewed: 2026-08-11
---

# Measurement plan — Midvex Lead Foundry

## Outcomes

| Outcome | Metric | Baseline | Target | Counter-metric | Source |
| --- | --- | --- | --- | --- | --- |
| Useful review queue | candidate precision/recall by rule/model | unknown | human acceptance decision after pilot | missed labelled candidates | evaluation dataset |
| Efficient review | review time and decision counts | unknown | measured, not guessed | correction/reversal count | privacy-minimised events |
| Bounded processing | cost/tokens per processed conversation | unknown | within configured job cap | unprocessed/failed jobs | model-run ledger |

## Funnel and event conventions

| # | Step | Event | Properties |
| --- | --- | --- | --- |
| 1 | source connected | `source_connected` | source type; no address |
| 2 | backfill completed | `backfill_completed` | counts, duration bucket, version |
| 3 | candidate viewed | `candidate_viewed` | opaque candidate ID, rule, locale |
| 4 | decision recorded | `candidate_decided` | decision, rule, model/prompt version |
| 5 | CSV exported | `export_completed` | record count, schema version |

Events are internal audit/measurement records only. They never contain message text, addresses, names, tokens, URLs, search queries or attachment contents. No third-party analytics runs in the pilot.

The accountable owner reviews the labelled pilot report before MVX-010–015 can become Ready.
