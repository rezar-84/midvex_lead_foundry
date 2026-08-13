---
status: draft
owner: product-manager
last-reviewed: 2026-08-13
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

**Now:** the product runs as a React SPA over a first-party JSON API (MVX-030..032): project workspaces, Gmail/IMAP/POP3/synthetic sources feeding one organisation-wide knowledge base, observable sync/analysis/enrichment jobs, contact history metrics, products, roles, tags and reviewable candidates. Auto-digest (MVX-034) chains analysis onto successful syncs per project; data quality (MVX-035) auto-merges exact duplicate contacts and queues fuzzy matches for human merge review. Only synthetic execution is currently authorised.

**Later:** MVX-002–015 harden authentication, prove real provider ingestion/scanning, calibrate analysis, and — per the expanded vision — build the enrichment agents: an Odoo CRM connector first (MVX-012), then other CRM/knowledge-base adapters, social signals, market-news monitoring and website summarisation for lead qualification (MVX-013), automated CRM entry updates, SaaS isolation and chat, each after its explicit gate.

**Not doing:** autonomous outreach; Gmail modification; automatic merges beyond exact-normalised-email contact dedup (fuzzy merges always human-reviewed); unapproved web scraping; indefinite ungoverned retention; real-data training of general models; CRM write-back before the connector milestone (MVX-012).

## Success metrics

| Outcome | Metric | Baseline | Target | Measured by |
| --- | --- | --- | --- | --- |
| Pilot exposes candidate quality | Precision/recall on an owner-labelled sample | unknown — MVX-006 establishes | reported honestly; owner acceptance gate | versioned evaluation set |
| Review remains safe | Unreviewed external writes | absent before implementation | zero | audit events/export manifests |
| Processing is reproducible | Candidates with source evidence and run version | unknown | every surfaced candidate | database constraints/tests |
| Cost is bounded | spend/token limit violations | unknown | zero unapproved overruns | model-run ledger |

## Constraints and dependencies

Private Dokploy deployment; balanced/capped cost; Turkish/English; one personal Gmail first. Real mailbox access, crawler source approval, processor approval, two Tier 1 approvers and retention decisions remain human dependencies U1–U5.
