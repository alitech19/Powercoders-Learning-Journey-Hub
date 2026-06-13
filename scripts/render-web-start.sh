#!/usr/bin/env sh
# Render web start. See docs/DEPLOY.md.
# Idempotent: migrate runs on every start.
set -e
cd "$(dirname "$0")/../backend"

python manage.py migrate --noinput

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
