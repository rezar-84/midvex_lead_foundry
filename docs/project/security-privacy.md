---
status: draft
owner: security
last-reviewed: 2026-08-11
---

# Security & privacy — Midvex Lead Foundry

## Data inventory

| Data | Purpose | Where | Retention/deletion |
| --- | --- | --- | --- |
| OAuth/processor credentials | authorised connector/provider access | encrypted DB/Dokploy secrets | revoke/rotate/disconnect |
| Raw MIME/attachments | evidence and reproducible parsing | encrypted object storage | required per-mailbox policy and purge job |
| Message/contact/company/product data | relationship reconstruction | PostgreSQL | same source policy; derived purge |
| Inferences/reviews/exports | opportunity workflow and audit | PostgreSQL/export file | policy plus explicit export disposal |
| Audit/operational metrics | accountability and reliability | PostgreSQL/log sink | separate configured period |

Lawful basis, jurisdictions, notices, processor agreements and exact periods are Unknown U2/U4. Production connection is blocked until resolved.

## Identity and controls

- Local accounts are admin-created; Argon2 passwords; TOTP MFA required; no public registration or privileged impersonation.
- Roles and object ownership follow `data-model-api.md`; enforcement is in organisation-scoped services/querysets, not hidden buttons.
- Secrets are injected, encrypted at rest, never logged, and treated as compromised when exposed.
- CSRF, secure cookies, restrictive hosts/origins, runtime validation, output escaping, SSRF restrictions and request limits default closed.
- Raw content, addresses, names, tokens and free-text never enter application logs or measurement events.
- Sign-in/failure, MFA, membership, OAuth, review, export, purge and privileged configuration changes are audited.

## Content and processors

Quarantined/unscanned content never reaches parsers or AI. AI/search integrations are disabled until a named provider, purpose, location, retention setting and agreement are approved. Data is not used to train general models. Prompt/model/schema/input versions and provider usage are recorded without logging source content.

Access, correction, export and deletion must traverse raw objects, parsed rows, embeddings, derived facts, caches, research artifacts and destination manifests. Backups expire under the recorded policy; immutable backup windows are disclosed rather than described as immediate deletion.

Suspected incidents follow contain → diagnose → fix → verify → log → postmortem. Notification obligations remain Unknown until U2 is resolved.
