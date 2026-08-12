#!/bin/sh
# Web-container entrypoint: apply migrations, then start gunicorn.
# The worker container does NOT use this (migrations run once, from web).
set -eu
python manage.py migrate --noinput
exec gunicorn lead_foundry.wsgi:application \
  --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-3}" --access-logfile -
