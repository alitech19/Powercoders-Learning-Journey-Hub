# TODO

Scheduled **tasks** (not infrastructure — Beat is in Docker/settings). Roadmap: [APP_PLAN.md](APP_PLAN.md).

- [ ] **Scheduled actions** — register in Beat when Slack is configured:
  - [x] `accounts.tasks.notify_missing_reflections` — weekly digest (integration reflections: `TAG_WEEKLY` + `final_reflection_at`).
  - [x] Slack on staff **feedback** and new user create/import (`accounts/emails.py`, `accounts/slack.py`).
  - [ ] Register schedule: Django admin → **Periodic tasks** (`django-celery-beat`) for `accounts.tasks.notify_missing_reflections`.
  - [ ] `SLACK_WEBHOOK_URL` + `SITE_URL` in production `.env`.
  - [ ] Tests: eager Celery + mock Slack for scheduled task (optional).

Configure Beat schedules in admin: http://localhost:8000/admin/django_celery_beat/

---

## Open questions — Slack (out of scope today)

**Today:** one staff `SLACK_WEBHOOK_URL` → single channel; students use in-app notifications + email toggle only.

- [ ] **Per-student Slack alerts?** — Can a student connect *their* Slack and get DMs for tasks, reflections due, feedback, group activity, etc.?
  - Likely needs Slack App + OAuth (`slack_user_id` on profile), event rules, opt-in per category, privacy review.
  - Alternative: strengthen email/in-app reminders instead of personal Slack.
- [ ] **Group chat ↔ Slack sync (flat, no threads)?** — Mirror `group_space` posts with a Slack channel per `cohorts.Group`; each message = one post (ignore / don’t use Slack threads).
  - Likely needs Slack App + Events API (not incoming webhook only), `slack_channel_id` per group, user mapping, dedup by `message_ts`, file/edit policy.
  - Start with one-way Hub → Slack before bidirectional sync.

Decide priority vs email/in-app before implementing either.
