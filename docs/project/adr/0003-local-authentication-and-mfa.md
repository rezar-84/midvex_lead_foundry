# ADR 0003 — Local accounts with mandatory MFA

- **Status:** Proposed
- **Date:** 2026-08-11
- **Deciders:** two named human approvers required
- **Work item:** MVX-001

## Context and decision

The company does not use Google Workspace identity. The pilot uses administrator-created Django accounts, Argon2 passwords, mandatory TOTP MFA, short server sessions and organisation roles. No self-registration, impersonation or password-email workflow is provided.

## Consequences

The team owns account recovery and MFA support. It gains attributable access without coupling application identity to mailbox OAuth. Shared-account and Google-SSO approaches were rejected for audit failure and unavailable organisation identity.

## Reversibility

Django authentication backends permit migration to a business identity provider; memberships and audit identities remain stable.
