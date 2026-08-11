# ADR 0001 — Modular Django monolith

- **Status:** Proposed
- **Date:** 2026-08-11
- **Deciders:** two named human approvers required
- **Work item:** MVX-001

## Context and decision

The pilot needs one security boundary, transactional review records, background ingestion and a private web UI. We use Python 3.14, Django 5.2 LTS, Celery 5.6, PostgreSQL, Redis and S3-compatible storage in one repository and release unit. Domain modules expose services; slow work runs in idempotent tasks.

## Consequences

This reduces cross-service authorisation and deployment cost but scales the application as a unit. A future independently scaling connector can be extracted only after its contract and load are evidenced. Separate SPA/microservices and an Odoo module were rejected for early boundary/operational cost and destination coupling.

## Reversibility

Modules and provider contracts make later extraction possible without changing canonical records. Trigger: measured workload or team ownership requires independent deployment.
