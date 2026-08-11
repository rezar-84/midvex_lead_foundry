---
status: accepted
owner: architect
last-reviewed: 2026-08-12
---

# ADR 0008 — Configuration-driven white-labelling and data-driven extraction profiles

## Context

Brand identity (header, TOTP issuer, crawler user-agent), extraction heuristics and
demo fixtures were compiled into the code as Midvex-specific constants, and an
organisation could only be created through `/admin`. The product decision (MVX-020)
is single-tenant white-labelling: any organisation self-hosts its own instance.

## Decision

Brand and locale come from environment settings (`FOUNDRY_BRAND_NAME`,
`FOUNDRY_USER_AGENT`, `DJANGO_LANGUAGE_CODE`/`DJANGO_LANGUAGES`) with defaults that
reproduce the previous behaviour; the Python package name is deliberately not
runtime brand. Extraction rules live in `foundry/heuristics.py` as
`DEFAULT_FIELD_RULES` and compile into a validated `CompiledProfile` (regex
validation, length/count caps against ReDoS). A project-scoped
`ExtractionProfile` row (entity type `message`, highest version wins) overrides any
rule; **no default rows are seeded** — absence means shipped defaults, so upgrading
the defaults upgrades every non-customised project and no backfill migration exists.
Provisioning is a CLI management command (`provision`), idempotent and
secret-safe; a first-run web wizard was rejected as an unauthenticated attack
surface (revisit under MVX-014).

## Consequences

A fresh install is brandable and provisionable without code changes or `/admin`.
Profile overrides make extraction behaviour a reviewable data change rather than a
code change, at the cost of a validation surface (mitigated by compile-time checks
and caps). Existing installs are unaffected: every default reproduces the previous
output, verified by a parity test.

## Rollback

Unset the new environment variables and delete any `ExtractionProfile` rows; the
system is behaviourally identical to the pre-MVX-020 build. No migration to
reverse.
