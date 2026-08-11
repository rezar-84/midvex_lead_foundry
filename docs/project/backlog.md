---
status: draft
owner: product-manager
last-reviewed: 2026-08-11
---

# Backlog — Midvex Lead Foundry

## Now

| ID | Task | Tier | Owner role | Depends on | Status |
| --- | --- | --- | --- | --- | --- |

## Next

| ID | Task | Tier | Owner role | Depends on | Status |
| --- | --- | --- | --- | --- | --- |
| MVX-002 | Complete account recovery, membership lifecycle and audit coverage around the MVP controls | 1 | security | MVX-001 | Ready |
| MVX-003 | Prove full-archive Gmail checkpoints and incremental reconciliation beyond the disabled connector scaffold | 1 | architect | MVX-002; Google OAuth credentials | Ready |
| MVX-004 | Add ClamAV/Rspamd inspection and safe extraction beyond fail-closed quarantine | 1 | security | MVX-003 | Ready |
| MVX-005 | Resolve products, duplicate identities and complete interaction timelines beyond header-derived candidates | 1 | architect | MVX-004 | Ready |
| MVX-006 | Calibrate rankings and generate scheduled digests against an authorised labelled set | 1 | product-manager | MVX-005; labelled evaluation set | Ready |
| MVX-007 | Extend accepted-only CSV v1 with destination mapping and delivery reconciliation | 1 | security | MVX-006 | Ready |
| MVX-008 | Prove Dokploy backup, restore, rollback and production budgets | 1 | devops-sre | MVX-002–007 | Ready |

## Blocked

| ID | Task | Tier | Owner role | Depends on | Status | Who can unblock | Since |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MVX-009 | Connect a real current or former-staff mailbox | 1 | privacy-legal | documented authority, purpose, retention and notices | Blocked | accountable human and qualified reviewer | 2026-08-11 |

## Parked — awaiting a human

| ID | Task | Tier | Owner role | Depends on | Status | Waiting on whom | For what decision | Since |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MVX-001 | Establish the governed standalone synthetic pilot foundation | 1 | architect | accountable human and two approvers before merge | Parked | accountable human and two named approvers | approve the Tier 1 foundation for merge; this does not authorise real data | 2026-08-11 |

## Later

| ID | Task | Tier | Owner role | Depends on | Status | Becomes relevant when |
| --- | --- | --- | --- | --- | --- | --- |
| MVX-010 | Add multiple Gmail and standards-based IMAP source adapters | 1 | architect | pilot quality accepted | Deferred | one-mailbox pilot is accepted |
| MVX-011 | Add metered public-web enrichment with approved source policies | 1 | privacy-legal | processor/source approval | Deferred | mail-only candidate quality is known |
| MVX-012 | Add an Odoo 19 JSON-2 destination adapter | 1 | architect | MVX-007 | Deferred | standalone review workflow is accepted |
| MVX-013 | Add additional CRM destination adapters | 1 | architect | MVX-012 | Deferred | a named customer CRM is prioritised |
| MVX-014 | Complete external Google OAuth verification and SaaS isolation gate | 1 | security | commercialisation decision | Deferred | external customer onboarding is authorised |
| MVX-015 | Add WhatsApp and other chat source adapters | 1 | privacy-legal | platform access and processing authority | Deferred | a specific channel/export path is approved |

## Done

| ID | Task | Tier | Owner role | Depends on | Status | Completed |
| --- | --- | --- | --- | --- | --- | --- |

## Dropped

| ID | Task | Tier | Owner role | Depends on | Status | Why dropped | When |
| --- | --- | --- | --- | --- | --- | --- | --- |
