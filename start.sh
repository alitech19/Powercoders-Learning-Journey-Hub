#!/usr/bin/env bash
# Render production start script.
# Runs once per deploy: migrate → collectstatic → create admin → start Gunicorn.
# "exec" replaces the shell with Gunicorn so it becomes PID 1 and receives signals.
set -e

echo "==> Applying database migrations..."
# One-time fix: the production DB has the full schema but django_migrations is
# missing records for many custom-app migrations. Django's migrate command calls
# check_consistent_history and then tries to re-apply already-applied DDL,
# causing DuplicateColumn / DuplicateTable errors. We insert every known
# migration record for every custom app with a WHERE NOT EXISTS guard so the
# row is added only when missing. This is safe to run on every deploy.
python manage.py shell -c "
from django.db import connection
rows = [
    # accounts
    ('accounts', '0001_initial'),
    ('accounts', '0002_user_cohort_user_group'),
    ('accounts', '0003_user_security_fields_auditlog'),
    ('accounts', '0004_rename_accounts_au_user_id_0a1b2c_idx_accounts_au_user_id_d4cccd_idx'),
    ('accounts', '0005_notification'),
    # cohorts
    ('cohorts', '0001_initial'),
    # feedback
    ('feedback', '0001_initial'),
    ('feedback', '0002_rename_feedback_fe_content_0a1b2c_idx_feedback_fe_content_364176_idx'),
    ('feedback', '0003_alter_feedbackentry_body'),
    # goals
    ('goals', '0001_initial'),
    ('goals', '0002_goal_achieved_at'),
    ('goals', '0003_goalenrollment_milestonecompletion_and_more'),
    ('goals', '0004_remove_legacy_goal_fields'),
    ('goals', '0005_clean_milestone_titles'),
    ('goals', '0006_remove_goalcomment_migrate_to_feedback'),
    ('goals', '0007_alter_goal_description_alter_goal_title_and_more'),
    # group_space
    ('group_space', '0001_initial'),
    ('group_space', '0002_backfill_group_spaces'),
    ('group_space', '0003_chat_ordering'),
    # habits
    ('habits', '0001_initial'),
    # journal
    ('journal', '0001_initial'),
    # reflections
    ('reflections', '0001_initial'),
    ('reflections', '0002_add_final_reflection_at'),
    ('reflections', '0003_add_expectations_at'),
    ('reflections', '0004_field_length_limits'),
    ('reflections', '0005_halve_field_limits'),
    # resources
    ('resources', '0001_initial'),
    ('resources', '0002_backfill_group_containers'),
    # tasks
    ('tasks', '0001_initial'),
    ('tasks', '0002_add_assignee_cohort'),
    ('tasks', '0003_alter_subtask_title_alter_task_description_and_more'),
    ('tasks', '0004_subtask_enrollment'),
    # workflows
    ('workflows', '0001_initial'),
    ('workflows', '0002_alter_workflow_description_alter_workflow_title_and_more'),
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
