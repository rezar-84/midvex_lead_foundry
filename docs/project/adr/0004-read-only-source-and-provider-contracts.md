# ADR 0004 — Read-only sources and bounded providers

- **Status:** Proposed
- **Date:** 2026-08-11
- **Deciders:** two named human approvers required
- **Work item:** MVX-001

## Context and decision

The first source is personal Gmail; future sources and destinations differ. `SourceConnector`, `AIProvider`, `SearchProvider` and `DestinationConnector` are internal contracts. Gmail requests only `gmail.readonly`. AI/search are disabled until configured and budgeted. CSV is the only pilot destination.

## Consequences

The pilot cannot send, label or delete Gmail and cannot automatically contact/export records. Provider swaps require contract tests rather than domain rewrites. IMAP, Odoo and chat adapters are later work items.

## Reversibility

Adapters are replaceable; canonical records preserve provider IDs and versions without making them primary keys.
