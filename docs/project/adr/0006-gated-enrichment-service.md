---
status: accepted
owner: security
last-reviewed: 2026-08-11
---

# ADR 0006 — Gated provenance-first enrichment service

## Context

Enrichment requires outbound requests based partly on untrusted message-derived domains. Unrestricted crawling risks SSRF, runaway cost, prohibited collection and unsupported inferred facts.

## Decision

Enrichment is disabled by default with project allowlists and budgets. Reject loopback, link-local, private, reserved and non-HTTP(S) targets; limit redirects, bytes, depth and per-host rate; record URL, fetch time and content hash; store extracted fields as candidates requiring review. “Learning” means versioned extraction profiles adjusted from reviewed fields, not automatic model training.

## Consequences

Enrichment is deliberately scoped and slower. Network and processor approval remain external gates. Facts stay traceable and can be rebuilt when a profile changes.

## Rollback

Disable enrichment, revoke worker egress, cancel queued jobs and retain or purge artifacts according to project policy.
