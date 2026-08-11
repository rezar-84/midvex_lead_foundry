---
status: accepted
owner: architect
last-reviewed: 2026-08-11
---

# ADR 0005 — Project-scoped operations and persisted jobs

## Context

One organisation may run distinct archive-recovery efforts with different purpose, sources, language, retention and cost limits. Sync, analysis and enrichment outlive an HTTP request and must be observable and retryable.

## Decision

Add `LeadProject` below `Organization`; sources, jobs, relations and enrichment profiles belong to one project and the same organisation. Persist job state and counters, reject duplicate active jobs per operation/target, and execute through task adapters. Existing evidence records gain an optional project link during compatibility.

## Consequences

The UI can expose a coherent project lifecycle and isolate operational budgets. Every service validates both organisation and project. Nullable compatibility links require a later backfill before they can become mandatory.

## Rollback

Stop workers, return navigation to the organisation dashboard and reverse the additive migration only if no project records must be retained.
