---
status: draft
owner: architect
last-reviewed: 2026-08-11
---

# Data model & interfaces — Midvex Lead Foundry

Every domain table carries an immutable organisation owner. Cross-organisation relationships are forbidden by service validation and composite/index constraints. Source evidence is append-oriented; corrections create review/fact records rather than rewriting source.

| Entity group | Includes | Lifecycle / deletion | Personal data |
| --- | --- | --- | --- |
| Access | Organisation, Membership, MFADevice | admin-managed; revoke immediately | yes |
| Source | MailboxConnection, SyncRun, SourceMessage, Attachment | policy-bound import/purge | yes/secret |
| Safety | SpamAssessment, AttachmentAssessment | versioned re-scan; purge with source | yes |
| Knowledge | Conversation, Contact, Company, ProductConcept, Interaction, DerivedFact, EvidenceCitation | derived/rebuildable; reviewable merges | yes/inferred |
| Review | OpportunityCandidate, ReviewDecision, Digest | versioned; retain audit under policy | yes/inferred |
| Integration | ModelRun, ResearchArtifact, ExportBatch/Record | provider/policy-bound | yes |
| Audit | AuditEvent | append-only in application; separately retained | operational |

Key invariants: unique provider message ID per mailbox; unique raw hash reference; evidence and candidate share an organisation; only clean messages enter analysis; only accepted candidates enter exports; model output records provider/model/prompt/schema/input hashes; deletion is an explicit audited job.

Internal contracts are `SourceConnector`, `AIProvider`, `SearchProvider` and `DestinationConnector`. They return validated dataclasses and never receive an unrestricted ORM/user object. CSV schema v1 contains stable foundry ID, record type, names/addresses/phones explicitly approved, opportunity status/reason, last communication timestamp and source-evidence IDs.

## Authorisation matrix

| Actor | Read source/knowledge | Review | Manage source/users | Export | Purge |
| --- | --- | --- | --- | --- | --- |
| Admin | allow | allow | allow | allow | allow with confirmation |
| Analyst | allow | suggest corrections | deny | deny | deny |
| Reviewer | allow | allow | deny | deny | deny |
| Exporter | approved records only | read decisions | deny | allow | deny |
| Revoked/expired/different organisation | deny/no leak | deny/no leak | deny/no leak | deny/no leak | deny/no leak |

Migrations are additive/expand-first and reversible unless a named human accepts a specific exception. Test/seed data is synthetic and lives in test fixtures, never copied from production.
