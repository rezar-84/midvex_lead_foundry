# Midvex Lead Foundry

Private, evidence-linked relationship intelligence for reviewing opportunities in authorised historical communications. The first connector is Gmail with the read-only OAuth scope. Real mailbox access is disabled by default.

## Local synthetic demo

Requires Python 3.14 and `uv`.

```bash
uv sync --all-extras --dev
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

The seed command uses reserved `.test` addresses and synthetic content only. It creates an “Archive recovery demo” project, a synthetic source, completed sync/analysis jobs, contacts, products and relationship metrics. The application requires MFA enrollment after sign-in.

## Production gates

Do not set `GMAIL_REAL_DATA_ENABLED=true` until authority, jurisdiction, retention, deletion, processor terms, two Tier 1 approvers, and rollback ownership are recorded. See [security and privacy](docs/project/security-privacy.md) and the [release runbook](docs/project/release-runbook.md).

Production requires PostgreSQL, Redis, S3-compatible private object storage, TLS termination, a stable Fernet key, Google OAuth credentials, and a strong Django secret. Copy `.env.example` into Dokploy secret configuration; do not commit a populated environment file.

## Architecture

The application is a modular Django monolith with Celery workers. Raw evidence is encrypted at rest by the configured object store, while PostgreSQL holds searchable metadata, entities, decisions, and hashes. Candidates remain suggestions until a human accepts, rejects, or defers them. Accepted candidates can be exported through the versioned CSV contract.

The authoritative project documentation starts at [docs/README.md](docs/README.md).
