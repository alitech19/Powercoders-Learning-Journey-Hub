# TODO

Scheduled **tasks** (not infrastructure — Beat is in Docker/settings). Roadmap: [APP_PLAN.md](APP_PLAN.md).

- [ ] **Scheduled actions** — port/adapt from `origin/Ali` when ready:
  - [ ] `accounts.tasks.notify_missing_reflections` + `accounts/slack.py` — weekly Slack for students missing `reflections.Reflection` (`period_type=weekly`, Monday `period_date`).
  - [ ] (Later) Slack on new staff **feedback** (`feedback` app).
  - [ ] (Later) Slack on new user signup / import.
  - [ ] Register schedules: Django admin → **Periodic tasks** (`django-celery-beat`) or `CELERY_BEAT_SCHEDULE` in settings.
  - [ ] `SLACK_WEBHOOK_URL` in `.env` (empty = no-op in dev).
  - [ ] Tests: `CELERY_TASK_ALWAYS_EAGER=True`; mock Slack; reflection edge cases.

Configure Beat schedules in admin: http://localhost:8000/admin/django_celery_beat/
