---
status: draft
owner: product-manager
last-reviewed: 2026-08-11
---

# Product brief — Midvex Lead Foundry

## Problem

Company relationship history is dispersed through a long-lived Gmail archive. The requester cannot systematically see who contacted the company, what was discussed, which products were mentioned, what remains unanswered, or which records deserve renewed human attention.

## Positioning

- **What this is:** a private historical relationship-intelligence and lead-review workspace.
- **Promise:** turn authorised communication archives into evidence-linked records and review queues without taking autonomous sales action.
- **Why this:** standalone ownership, source provenance and human approval rather than coupling analysis to one CRM.
- **Alternatives today:** manual Gmail search, spreadsheets, CRM history and no systematic review.

## Audiences

| Audience | Job | Evidence needed | Next action |
| --- | --- | --- | --- |
| Administrator | Connect and govern an authorised source | sync state, policy and audit trail | authorise or stop processing |
| Analyst | Understand relationships and history | source-linked facts and timelines | correct entities and classify interactions |
| Reviewer | Decide whether a candidate is useful | reasons, evidence, uncertainty | accept, reject or defer |
| Exporter | Move approved records elsewhere | reviewed field map and manifest | download CSV; CRM later |

## Scope

**Now:** MVX-002–008 deliver one-account read-only Gmail ingestion, spam/attachment gates, linked knowledge, deterministic and AI-assisted candidates, in-app digests, review and CSV.

**Later:** MVX-010–015 add IMAP, enrichment, CRM adapters, SaaS and chat after explicit gates.

**Not doing:** autonomous outreach; Gmail modification; automatic merges; unapproved web scraping; indefinite ungoverned retention; real-data training of general models; CRM-first architecture.

## Success metrics

| Outcome | Metric | Baseline | Target | Measured by |
| --- | --- | --- | --- | --- |
| Pilot exposes candidate quality | Precision/recall on an owner-labelled sample | unknown — MVX-006 establishes | reported honestly; owner acceptance gate | versioned evaluation set |
| Review remains safe | Unreviewed external writes | absent before implementation | zero | audit events/export manifests |
| Processing is reproducible | Candidates with source evidence and run version | unknown | every surfaced candidate | database constraints/tests |
| Cost is bounded | spend/token limit violations | unknown | zero unapproved overruns | model-run ledger |

## Constraints and dependencies

Private Dokploy deployment; balanced/capped cost; Turkish/English; one personal Gmail first. Real mailbox access, processor approvals, two Tier 1 approvers and retention decisions remain human dependencies U1–U4.
