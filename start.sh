#!/usr/bin/env bash
# Render production start script.
# Runs once per deploy: migrate → collectstatic → create admin → start Gunicorn.
# "exec" replaces the shell with Gunicorn so it becomes PID 1 and receives signals.
set -e

echo "==> Applying database migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Creating initial admin user (if not already present)..."
python manage.py create_dev_superuser || true

echo "==> Starting Gunicorn on port ${PORT:-10000}..."
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120 \
  --log-level info
