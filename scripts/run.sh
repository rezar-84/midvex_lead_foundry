#!/usr/bin/env bash
# Dev launcher: sync deps, migrate, optionally seed demo data, run the server.
#
#   ./scripts/run.sh            # sync + migrate + runserver
#   ./scripts/run.sh --seed     # also create the synthetic demo workspace
#   PORT=8080 ./scripts/run.sh  # custom port (default 8000)
#
# Dev defaults need no external services: SQLite, filesystem evidence storage,
# eager Celery. External network execution stays disabled by policy.
set -euo pipefail
cd "$(dirname "$0")/.."

uv sync --all-extras --dev
uv run python manage.py migrate

if [[ "${1:-}" == "--seed" ]]; then
  uv run python manage.py seed_demo
  needs_password=$(uv run python manage.py shell -c "
from django.contrib.auth import get_user_model
user = get_user_model().objects.filter(username='demo').first()
print('yes' if user and not user.has_usable_password() else 'no')
")
  if [[ "${needs_password}" == *yes* ]]; then
    echo "The 'demo' admin has no password yet - set one now (12+ characters):"
    uv run python manage.py changepassword demo
  fi
fi

echo "Starting on http://127.0.0.1:${PORT:-8000}/ (sign-in requires MFA enrolment)"
exec uv run python manage.py runserver "${PORT:-8000}"
