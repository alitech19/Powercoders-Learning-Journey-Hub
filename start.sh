#!/usr/bin/env bash
# Render production start script.
# Runs once per deploy: migrate → collectstatic → create admin → start Gunicorn.
# "exec" replaces the shell with Gunicorn so it becomes PID 1 and receives signals.
set -e

echo "==> Applying database migrations..."
# One-time fix: production DB is missing group_space.0003_chat_ordering from
# django_migrations even though resources.0001_initial (which depends on it)
# is already recorded. Django's migrate command calls check_consistent_history
# before doing anything — including before --fake — so we must insert the row
# directly via the shell (which has no migration checks). The INSERT is
# idempotent: it does nothing if the row already exists.
python manage.py shell -c "
from django.db import connection
with connection.cursor() as c:
    c.execute(\"\"\"
        INSERT INTO django_migrations (app, name, applied)
        SELECT 'group_space', '0003_chat_ordering', NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM django_migrations
            WHERE app = 'group_space' AND name = '0003_chat_ordering'
        )
    \"\"\")
print('Migration history fix: group_space.0003_chat_ordering ensured.')
" || true
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
