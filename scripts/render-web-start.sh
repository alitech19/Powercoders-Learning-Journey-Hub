#!/usr/bin/env sh
# Render free tier: no pre-deploy — run DB setup before Gunicorn on each web start.
# Idempotent (migrate + dev seed use update_or_create). See docs/DEPLOY.md
set -e
cd "$(dirname "$0")/../backend"
python manage.py migrate --noinput
python manage.py create_dev_superuser
python manage.py seed_dev_data
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 120
