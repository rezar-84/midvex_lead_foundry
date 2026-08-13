---
status: active
owner: Rezar86
last-reviewed: 2026-08-13
---

# Project charter — Midvex Lead Foundry

## Identity

| | |
| --- | --- |
| **Project** | Midvex Lead Foundry |
| **What it is** | A private, white-label relationship-intelligence application that mines authorised historical communications (multiple mailboxes, one organisation-wide knowledge base) into evidence-linked sales leads, with human review of every candidate, optional auto-digest extraction, and audited contact dedup. |
| **Work item prefix** | `MVX` |
| **Repository** | `/home/rubuntu/Projects/midvex_lead_foundry` |
| **Accountable human** | Rezar86 (paraxweb@gmail.com) — recorded 2026-08-12; see ADR 0007. |

## Stack

| Concern | This project uses |
| --- | --- |
| Language / runtime | Python 3.14 |
| Package manager | uv |
| Framework(s) | Django 5.2 LTS; Celery 5.6; django-ninja (first-party JSON API at /api/) |
| Data store | PostgreSQL 17; Redis; S3-compatible encrypted object storage |
| Auth | Local Django accounts, Argon2 passwords, mandatory TOTP MFA, organisation-scoped RBAC |
| Hosting | Private Dokploy container stack |
| CI | Repository-local checks; hosted CI unknown |
| Test tooling | pytest, pytest-django, Ruff, mypy, Bandit, pip-audit; tsc + Vite build as the frontend gate |
| Frontend | React 19 + Vite + TypeScript + Tailwind 4 + shadcn/ui SPA in `frontend/` (npm), served by Django via catch-all + WhiteNoise |

## Constraints

| | |
| --- | --- |
| **Team / who maintains this** | Unknown; architecture minimises independently operated services. |
| **Operational capacity** | Dokploy; no on-call arrangement reported. |
| **Budget ceiling** | Unknown; deterministic filtering, caching and per-job AI/search budgets are mandatory. |
| **Latency / throughput** | Interactive review pages; resumable background processing. Numeric budgets are not yet evidenced. |
| **Existing platform commitments** | Standalone product; optional Odoo 19 and other CRM adapters later. |
| **Timeline** | No fixed delivery date reported; pilot-first sequence. |

## Commands

| Stage | Command |
| --- | --- |
| Install | `uv sync --all-extras --dev` |
| Run locally | `uv run python manage.py runserver` (+ `npm --prefix frontend run dev` for the SPA) |
| `checks.format` | `uv run ruff format --check .` |
| `checks.lint` | `uv run ruff check .` |
| `checks.typecheck` | `uv run mypy foundry lead_foundry` |
| `checks.unit` | `uv run pytest -m 'not integration and not contract'` |
| `checks.integration` | `uv run pytest -m integration` |
| `checks.contract` | `uv run pytest -m contract` |
| `checks.build` | `uv build` |
| `checks.scan` | `uv run bandit -q -r foundry lead_foundry && uv run pip-audit` |
| `checks.a11y` | `uv run python scripts/check_a11y.py` (surviving login/MFA templates only; SPA a11y pass deferred) |
| `checks.frontend` | `npm --prefix frontend run typecheck && npm --prefix frontend run build` |
| `checks.e2e` | `uv run pytest -m e2e` |

## Environments

| Environment | Purpose | Deployed from | Who may deploy |
| --- | --- | --- | --- |
| local | Development with synthetic data | work-item branch | developer |
| staging | Dokploy verification with synthetic/redacted data | reviewed branch | named operator required |
| production | Authorised company archive | approved release | named operator required |

| | |
| --- | --- |
| **Default branch** | `main` |
| **Direct commits to it** | not allowed |

## Active roles

| Role | Active | Reason if inactive |
| --- | --- | --- |
| product-manager | ☑ | |
| architect | ☑ | |
| security | ☑ | |
| qa | ☑ | |
| ux-designer | ☑ | |
| brand-designer | ☑ | |
| copywriter | ☑ | |
| accessibility | ☑ | |
| devops-sre | ☑ | |
| privacy-legal | ☑ | |
| cro-analyst | ☑ | |
| seo | ☐ | No publicly discoverable content is in scope. |

## Risk defaults

| | |
| --- | --- |
| **Always Tier 1 here** | Mailbox access, personal data, authentication, exports, AI processing, retention/deletion, tenant isolation, deployment. |
| **Never Tier 1 here** | None declared. |
| **Human approval required for** | Real mailbox connection, production deployment, data deletion, external AI/search processing, CRM export, customer onboarding. |
| **Approvers** | Rezar86 (sole approver under the solo-operator model, ADR 0007; the two-approver rule resumes when a second maintainer exists or MVX-009 opens). |
| **Staleness threshold** | 90 days |

## Standards & targets

| | |
| --- | --- |
| **Accessibility target** | WCAG 2.2 AA |
| **Assistive technologies supported** | Browser keyboard navigation; screen-reader pairs not yet verified. |
| **Supported platforms / browsers / sizes** | Current desktop/mobile evergreen browsers; exact matrix pending verification. |
| **Languages & writing directions** | Turkish and English; left-to-right. |
| **Performance budgets** | Unmeasured; MVX-008 establishes production budgets. |
| **Primary outcome** | A reviewer accepts or rejects an evidence-backed opportunity candidate. |
| **Jurisdictions / regimes** | Unknown; real-data processing is gated on qualified confirmation. |
| **Data categories held** | Message content/metadata, attachments, identities, contact/company details, inferred interactions/opportunities, credentials, audit data. |

## Sources of truth

| Thing | Where |
| --- | --- |
| Brand guidelines | Absent; `design-system.md` defines the internal pilot UI. |
| Design tokens | `foundry/static/foundry/app.css` |
| Analytics / search data | Internal privacy-minimised events and PostgreSQL records. |
| Content source | Authorised mailboxes and provenance-linked public research. |
| Secrets | Dokploy secrets/environment injection; never the repository. |
| Issue tracker | `backlog.md` |

## Artifacts in use

☑ product-brief ☐ discovery-audit ☑ user-stories ☑ architecture ☑ data-model-api
☑ design-system ☐ content-seo-plan ☑ measurement-plan ☑ security-privacy
☑ threat-model ☑ test-plan ☑ release-runbook
