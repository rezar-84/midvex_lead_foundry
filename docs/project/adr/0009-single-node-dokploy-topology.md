---
status: accepted
owner: devops-sre
last-reviewed: 2026-08-12
---

# ADR 0009 — Single-node Dokploy production topology

## Context

The pilot deploys to one Dokploy host at `mlf.midvex.com`. The charter's stack
names PostgreSQL/Redis/S3, but no S3-compatible store is provisioned yet, and
migrations previously had no automated execution point.

## Decision

One compose stack (web + celery worker + postgres + redis) on the Dokploy host.
Migrations run from the web container's entrypoint only (single web replica; the
worker never migrates). Evidence storage defaults to a named Docker volume via the
already-supported filesystem backend, with `RAW_STORAGE_BACKEND=s3` as the
configuration-only upgrade path once object storage exists. TLS terminates at
Dokploy's proxy; the app trusts `X-Forwarded-Proto`. Policy gates
(`SOURCE_NETWORK_ENABLED`, `GMAIL_REAL_DATA_ENABLED`, `ENRICHMENT_NETWORK_ENABLED`)
ship false and are excluded from this decision.

## Consequences

Deploys are one-step and repeatable; the trade-offs are single-node ones: no HA,
volume-level durability for evidence until S3, and entrypoint migrations assume one
web replica (scaling web horizontally requires moving migrations to a release
step). Backup/restore/rollback drills remain MVX-008 and block calling this
production-proven.

## Rollback

Redeploy the prior image via Dokploy; reverse only verified migrations per the
release runbook; volumes persist across redeploys.
