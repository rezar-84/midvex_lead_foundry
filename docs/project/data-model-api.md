---
status: draft
owner: architect
last-reviewed: 2026-08-13
---

# Data model & interfaces — Midvex Lead Foundry

Every domain table carries an immutable organisation owner. Cross-organisation relationships are forbidden by service validation and composite/index constraints. Source evidence is append-oriented; corrections create review/fact records rather than rewriting source.

| Entity group | Includes | Lifecycle / deletion | Personal data |
| --- | --- | --- | --- |
| Access | Organisation, Membership, MFADevice | admin-managed; revoke immediately | yes |
| Operations | LeadProject, LeadSource, BatchJob/Item | project policy; persisted progress and safe errors | yes/secret |
| Source | MailboxConnection, SyncRun, SourceMessage, Attachment | policy-bound import/purge | yes/secret |
| Safety | SpamAssessment, AttachmentAssessment | versioned re-scan; purge with source | yes |
| Knowledge | Conversation, Contact, Company, ProductConcept, Interaction, DerivedFact, EvidenceCitation | derived/rebuildable; reviewable merges | yes/inferred |
| Taxonomy | ProjectEntity, Tag/EntityTag, EntityRelationship, ContactMetric | project-scoped; rebuild metrics, preserve reviewed tags | yes/inferred |
| Data quality | MergeSuggestion (fuzzy duplicate pairs awaiting review; exact merges are automatic and audit-logged as `contact.merged`) | pending rows persist; accepted rows disappear with the merged contact | yes |
| Enrichment | ExtractionProfile, EnrichmentResult | URL/hash provenance; candidate review; project budget/allowlist. ExtractionProfile (entity type `message`) overrides the shipped extraction rules per project; absence means the code defaults in `foundry/heuristics.py` apply. | yes/inferred |
| Review | OpportunityCandidate, ReviewDecision, Digest | versioned; retain audit under policy | yes/inferred |

**Reserved (schema exists, no writer yet):** `ModelRun` and `Digest` belong to
MVX-006, `ResearchArtifact` to MVX-011; `BatchJob.configuration`/
`rate_limit_remaining` to MVX-010 and `ProjectEntity.review_status` to MVX-005.
Dropping any of them is destructive and deferred to MVX-022.
| Integration | ModelRun, ResearchArtifact, ExportBatch/Record | provider/policy-bound | yes |
| Audit | AuditEvent | append-only in application; separately retained | operational |

`LeadProject.auto_digest_enabled` (MVX-034) chains an `analyze` BatchJob onto each successful sync; `BatchJob.kind` now includes `dedup` (MVX-035).

Key invariants: unique provider message ID per mailbox; unique raw hash reference; project/source/job/entity links share an organisation; one queued/running operation per project-kind-target; only clean messages enter analysis; credentials never render; only accepted candidates enter exports; enrichment results retain URL/hash/profile provenance; deletion is an explicit audited job.

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

## First-party JSON API (MVX-030..035)

The SPA consumes `/api/` (django-ninja). Session-cookie auth + CSRF header; MFA middleware
returns `401 {"error": {"code": "mfa_required"}}` on `/api/*`; capability checks mirror the
former view decorators; validation errors return
`400 {"error": {"code": "validation_error", "message", "fields"}}`. Paginated lists use
`{items, count, page, pages, per_page}`. This is not a third-party API surface.

| Group | Endpoints (prefix `/api`) | Capability |
| --- | --- | --- |
| Session | `GET /me` | view |
| Review loop | `GET /dashboard`, `GET /opportunities(+/{id})`, `POST /opportunities/{id}/review`, `GET /conversations`, `GET /knowledge` | view; review for decisions |
| Projects | `GET/POST /projects`, `GET/PATCH /projects/{id}` | view; manage_projects for writes |
| Sources | `GET/POST /projects/{id}/sources`, `GET/PATCH …/{sid}`, `POST …/{sid}/sync`; `GET /sources` (org mailboxes) | manage_sources (view for reads) |
| Jobs | `POST /projects/{id}/analysis/start`, `GET /projects/{id}/jobs(+/{jid})`, `POST …/{jid}/cancel` | run_batches for writes |
| Entities | `GET /projects/{id}/contacts(+/{cid})`, `POST …/contacts/tags/assign`, `GET/POST …/tags`, `GET/POST …/products` | view / run_batches |
| Enrichment | `POST /projects/{id}/enrichment/start`, `POST …/enrichment/{rid}/review` | run_enrichment / review |
| Data quality | `POST /projects/{id}/dedup/start`, `GET /merge-suggestions`, `POST /merge-suggestions/{id}/decide` | run_batches / view / review |
| Settings | `GET /instance-settings`, `PUT /instance-settings/{key}` | manage_users |

Outside `/api/`: login/MFA templates, `POST /exports/csv/` (file download) and the Gmail
OAuth handshake at `/integrations/gmail/…` (full-page redirects).
