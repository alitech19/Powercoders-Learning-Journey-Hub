#!/usr/bin/env bash
# Render production start script.
# Runs once per deploy: migrate → collectstatic → create admin → start Gunicorn.
# "exec" replaces the shell with Gunicorn so it becomes PID 1 and receives signals.
set -e

echo "==> Applying database migrations..."
# One-time fix: production DB is missing several group_space migration records
# even though later migrations that depend on them are already recorded.
# Django's migrate calls check_consistent_history before doing anything
# (including before --fake), so we insert the missing rows directly via the
# shell (no migration checks run there). All INSERTs are idempotent.
python manage.py shell -c "
from django.db import connection
rows = [
    ('group_space', '0001_initial'),
    ('group_space', '0002_backfill_group_spaces'),
    ('group_space', '0003_chat_ordering'),
]
with connection.cursor() as c:
    for app, name in rows:
        c.execute('''
            INSERT INTO django_migrations (app, name, applied)
            SELECT %s, %s, NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM django_migrations
                WHERE app = %s AND name = %s
            )
        ''', [app, name, app, name])
        print(f'Migration history fix: {app}.{name} ensured.')
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
