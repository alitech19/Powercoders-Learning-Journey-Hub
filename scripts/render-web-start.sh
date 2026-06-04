#!/usr/bin/env sh
# Render web start (integration). See docs/DEPLOY.md — branch deploy, not main render-start.sh.
# Idempotent: migrate every start; dev superuser/seed only when env flags allow (DEBUG=True tester).
set -e
cd "$(dirname "$0")/../backend"

python manage.py migrate --noinput

if [ "${CREATE_DEV_SUPERUSER}" = "true" ]; then
  python manage.py create_dev_superuser || echo "create_dev_superuser: skipped or already exists"
fi

if [ "${ENABLE_DEV_SEED}" = "true" ]; then
  python manage.py seed_dev_data || echo "seed_dev_data: skipped (requires DEBUG=True)"
fi

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
