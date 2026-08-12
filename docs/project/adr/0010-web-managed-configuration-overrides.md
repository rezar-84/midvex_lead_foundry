---
status: accepted
owner: security
last-reviewed: 2026-08-12
---

# ADR 0010 — Web-managed configuration overrides

## Context

The user asked to add and edit API keys (Google OAuth and related) from the
product UI. Configuration was environment-only (ADR 0009); the instance settings
page (MVX-027) was read-only.

## Decision

A whitelist of keys (`foundry/runtime_settings.EDITABLE_KEYS`) may be overridden
from the admin-only settings page. Overrides live in `InstanceSetting` rows,
Fernet-encrypted with `TOKEN_ENCRYPTION_KEY`; `runtime_setting()` resolves DB
override → environment fallback, and clearing a field deletes the override.
Secrets are write-only: the page never renders a stored value. Every change is
audit-logged. Deliberately not editable: the policy gates
(`SOURCE_NETWORK_ENABLED`, `GMAIL_REAL_DATA_ENABLED`,
`ENRICHMENT_NETWORK_ENABLED` — the human-approval surface), `SECRET_KEY`,
`TOKEN_ENCRYPTION_KEY`, and infrastructure URLs.

## Consequences

Operators can configure Google OAuth without redeploying. The database now holds
encrypted credentials, so its backups are as sensitive as the Fernet key;
rotating `TOKEN_ENCRYPTION_KEY` invalidates overrides along with the other
encrypted fields. Gates remain impossible to enable from the web.

## Rollback

Delete `InstanceSetting` rows (environment values resume immediately) and revert
the migration; consumers fall back transparently.
