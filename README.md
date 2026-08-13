# Midvex Lead Foundry

Private, white-label relationship intelligence. An organisation connects its authorised historical communications — Gmail read-only first, with IMAP/POP3 and synthetic adapters — and Lead Foundry mines them into evidence-linked sales leads: contacts, companies, products and opportunities, each traceable to the source messages that support it. Multiple mailboxes and sources feed one organisation-wide knowledge base; with auto-digest enabled, every successful sync triggers analysis automatically. Every extracted candidate stays a suggestion until a person accepts, rejects or defers it, and the data-quality workflow auto-merges only exact duplicate contacts while fuzzy matches wait for human review. Real mailbox access is disabled by default.

## Local synthetic demo

Requires Python 3.14, `uv`, and Node.js with npm for the frontend.

```bash
./scripts/run.sh --seed   # sync, migrate, seed demo data, set demo password, runserver
```

Or step by step:

```bash
uv sync --all-extras --dev
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py changepassword demo
uv run python manage.py runserver
```

For frontend development, run the Vite dev server alongside the Django backend on :8000:

```bash
cd frontend
npm install
npm run dev        # serves the SPA on :5173, proxying API calls to :8000
```

The frontend gate before shipping is `npm run typecheck && npm run build`. Production images build the SPA in the multi-stage Dockerfile (node builds `frontend/dist`, then Python `collectstatic` picks it up).

The seed command uses reserved `.test` addresses and synthetic content only. It creates an “Archive recovery demo” project, a synthetic source, completed sync/analysis jobs, contacts, products and relationship metrics. The application requires MFA enrollment after sign-in.

## Self-hosting for your own organisation

The product is white-label: any organisation can run its own instance.

```bash
FOUNDRY_ADMIN_PASSWORD='choose-a-strong-password' \
  uv run python manage.py provision --org-name "Acme Leads" --username acme-admin
```

`provision` is idempotent — it creates the organisation, the first admin account and
the admin membership, and never prints the password. Configure the instance through
environment variables (see `.env.example`): `FOUNDRY_BRAND_NAME` sets the header,
page titles and TOTP issuer; `FOUNDRY_USER_AGENT` identifies the enrichment fetcher;
`DJANGO_LANGUAGE_CODE`/`DJANGO_LANGUAGES`/`DJANGO_TIME_ZONE` set the locale.

Entity extraction is driven by per-project **extraction profiles**
(`foundry/heuristics.py`): a project without a profile row uses the shipped default
rules, and a project-scoped `ExtractionProfile` row (entity type `message`) can
override any rule pattern. Rules are validated regex strings — invalid or oversized
patterns are rejected.

## Deploying on Dokploy (mlf.midvex.com)

1. In Dokploy create a **Docker Compose** application pointing at this repository
   (`compose.yaml` at the root). Every push to `main` can auto-deploy, or deploy a
   pinned commit.
2. Copy `.env.production.example` into the application's environment configuration
   and replace every `replace-*` value. Generate the two secrets:
   `python -c "import secrets; print(secrets.token_urlsafe(64))"` for
   `DJANGO_SECRET_KEY`, and
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   for `TOKEN_ENCRYPTION_KEY` (losing this key orphans stored credentials).
3. Add the domain **mlf.midvex.com** to the `web` service (container port 8000)
   with HTTPS/Let's Encrypt enabled. TLS terminates at Dokploy's proxy; the app
   trusts `X-Forwarded-Proto` and redirects HTTP itself.
4. First deploy: the web container applies migrations automatically
   (`scripts/docker-entrypoint.sh`), then provision your organisation:
   `uv run python manage.py provision --org-name "Midvex" --username <you>`
   from the web container's terminal (set `FOUNDRY_ADMIN_PASSWORD` for
   non-interactive use). Sign in and enrol MFA.
5. Evidence storage defaults to the `evidence_data` volume
   (`RAW_STORAGE_BACKEND=filesystem`); switch to S3-compatible storage by setting
   `RAW_STORAGE_BACKEND=s3` and the `S3_*` values. Back up the `postgres_data` and
   `evidence_data` volumes together — backup/restore drills are MVX-008.
6. Keep the three network policy gates `false` (see Production gates below).

## Production gates

Do not set `GMAIL_REAL_DATA_ENABLED=true` until authority, jurisdiction, retention, deletion, processor terms, two Tier 1 approvers, and rollback ownership are recorded. See [security and privacy](docs/project/security-privacy.md) and the [release runbook](docs/project/release-runbook.md).

Production requires PostgreSQL, Redis, S3-compatible private object storage, TLS termination, a stable Fernet key, Google OAuth credentials, and a strong Django secret. Copy `.env.example` into Dokploy secret configuration; do not commit a populated environment file.

## Architecture

The application is a modular Django monolith with Celery workers. The UI is a React 19 + Vite + TypeScript + Tailwind 4 + shadcn/ui single-page app in `frontend/`, served by Django through a catch-all view (built assets via WhiteNoise) and talking to a first-party, session-authenticated JSON API mounted at `/api/` (django-ninja). This is not a public API — same origin, same session, same capability checks as before. Login and MFA pages remain server-rendered Django templates, and CSV export remains a Django POST endpoint. Raw evidence is encrypted at rest by the configured object store, while PostgreSQL holds searchable metadata, entities, decisions, and hashes. Candidates remain suggestions until a human accepts, rejects, or defers them. Accepted candidates can be exported through the versioned CSV contract.

The authoritative project documentation starts at [docs/README.md](docs/README.md).
