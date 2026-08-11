# ADR 0002 — Evidence storage and organisation ownership

- **Status:** Proposed
- **Date:** 2026-08-11
- **Deciders:** two named human approvers required
- **Work item:** MVX-001

## Context and decision

Raw communication evidence is large and sensitive; derived records must remain traceable and future tenant-safe. Raw MIME and attachments use encrypted S3-compatible objects. PostgreSQL stores metadata, relationships, facts, citations, reviews and audit events. Every domain row has immutable organisation ownership; services scope every query and validate cross-record ownership.

## Consequences

Object storage backup/deletion joins the operational burden. Evidence can be reparsed without silently rewriting source. SaaS still requires a separate adversarial isolation gate; pilot structure is not a compliance claim. Database-only blobs and a dedicated graph database were rejected for growth/backup cost and unproven need.

## Reversibility

Object keys and content hashes permit migration to another compatible store. Adjacency records can be projected into a graph store later.
