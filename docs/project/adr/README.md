# Architecture Decision Records

One file per durable decision: `NNNN-short-slug.md`, from `../../templates/adr.md`.

## When to write one

Write an ADR when the decision is **expensive to reverse**, or when a future reader would
otherwise have to reverse-engineer the reasoning from the code.

Typically: stack, storage, and hosting choices · authentication and authorisation model ·
tenancy or isolation model · the shape of an interface others depend on · a significant
new dependency · a data model others will build on · **anything chosen against the
obvious option**.

Not: naming, formatting, or anything a lint rule can express.

Rules — numbering, the status lifecycle, superseding rather than editing, and recording
the real reason an option lost — are in `../../process/05-change-control.md`,
"Architecture Decision Records".

## Index

| # | Decision | Status | Date |
| --- | --- | --- | --- |
| 0001 | Modular Django monolith | Proposed | 2026-08-11 |
| 0002 | Evidence storage and organisation ownership | Proposed | 2026-08-11 |
| 0003 | Local accounts with mandatory MFA | Proposed | 2026-08-11 |
| 0004 | Read-only sources and bounded providers | Proposed | 2026-08-11 |
| 0005 | Project-scoped operations and persisted jobs | Accepted | 2026-08-11 |
| 0006 | Gated provenance-first enrichment service | Accepted | 2026-08-11 |
| 0007 | Solo-operator approval model | Accepted | 2026-08-12 |
| 0008 | Configuration-driven white-labelling and extraction profiles | Accepted | 2026-08-12 |
| 0009 | Single-node Dokploy production topology | Accepted | 2026-08-12 |
