# TODO — Potential features & plans

Index of planned capabilities. Implementation details live in the linked docs.

Deploy and Beat setup: [DEPLOY.md](../DEPLOY.md) · Local: [SETUP.md](../SETUP.md)

---

## Near-term ops (no separate plan)

- [x] Global reminder schedule via **Administration → Notifications** (`/admin-config/notifications/`) — saves Celery Beat tasks automatically
- [ ] Production env: `SLACK_WEBHOOK_URL`, `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SITE_URL`
- [ ] After deploy: `python manage.py migrate` on web + beat services

Beat admin: http://localhost:8000/admin/django_celery_beat/periodictask/

Expected periodic tasks (created on migrate or when saving Notification Management):

| Task name | Celery task |
|-----------|-------------|
| Hourly deadline reminders | `accounts.tasks.run_deadline_reminders_task` |
| Weekly missing-reflections digest | `accounts.tasks.notify_missing_reflections` |
| Hourly notification digests | `accounts.tasks.dispatch_hourly_notification_digests_task` |
| Daily notification digests | `accounts.tasks.dispatch_daily_notification_digests_task` |
| Weekly DB backup | `config.tasks.backup_database` |

---

## Slack integration

Plan: **[SLACK_INTEGRATION_PLAN.md](SLACK_INTEGRATION_PLAN.md)**

| Feature | Status |
|---------|--------|
| Global staff webhook (feedback, new user, missing reflections digest) | Done |
| Per-user notification settings (in-app / email / Slack toggles) | Done |
| Unified notification dispatcher (dedupe, delivery log) | Done |
| Per-user Slack OAuth (connect / disconnect) | Done |
| Personal Slack DM via dispatcher | Done |
| Assignment notifications (task / goal / workflow) | Done |
| Slack DM: feedback, new task/goal/workflow, deadline reminders | Done |
| Digest mode (hourly / daily email + Slack) | Done |
| Global reminder admin UI (deadline + reflection digest schedule) | Done |
| Group chat in-app / email / Slack (mentions + all messages) | Done |
| Group chat → Slack channel sync (one-way) | Done |
| Group chat ↔ Slack (two-way) + thread → flat reply links | Done |
| Slack message edit/delete sync | Planned |

---

## Scheduling & reminders

Plan: **[SCHEDULING_AND_REMINDERS_PLAN.md](SCHEDULING_AND_REMINDERS_PLAN.md)**

| Feature | Status |
|---------|--------|
| Scheduled publish (`publish_at`) for task / goal / workflow | Planned |
| Entity deadline reminders (24h, 2h, overdue) | Done |
| Global reminder schedule (admin UI + Celery Beat) | Done |
| Standalone reminders — one-time (staff) | Planned |
| Standalone reminders — recurring (daily / weekly / monthly) | Planned |
| Central scheduler (`ScheduledAction`) + delivery log | Planned |
| Rate limit: 1 batch/min, jitter, multi-message batches | Planned |
| UI: Schedule block on entity forms; staff **Automation / Reminders** page | Planned |

Timezone: **Europe/Zurich** (all schedules).

---

## Google Drive & resources storage

Setup: **[GOOGLE_DRIVE_SETUP.md](../GOOGLE_DRIVE_SETUP.md)** · in-app **Administration → File storage** (ⓘ) · `/info/google_drive/`

| Feature | Status |
|---------|--------|
| **Staff** uploads → org **Shared drive** (`PowerHUB/Groups/…`, service account) | Done |
| **Student** uploads → uploader’s **My Drive** (OAuth) | Done |
| Create Google Doc / Sheet / Slides / Form from group chat | Done |
| Staff **Contributor** / admin **Content manager**; delete org files **admin only** | Done |
| Admin **storage settings** (web + Django admin) — Google creds in DB, not `.env` | Done |
| Staff turnover: files stay in Shared drive; new teachers via drive membership | Done (IT process) |
| Auto share **anyone with the link** (students open staff files without Shared drive ACL) | Done |
| Student Google OAuth (email must match `User.email`) | Done |
| Resources tiles use `webViewLink` | Done |
| Upload retry in chat, rate limits, admin upload log / connections | Done |
| Legacy local `media/group_files/` (read-only / migration) | Sunset — new uploads go to Drive only |

**Follow-up (no separate plan):** `PowerHUB/Projects/{space}/` folders when [project spaces](GROUP_SPACE_PROJECT_PLAN.md) ship.

---

## Project spaces (custom collaboration)

Plan: **[GROUP_SPACE_PROJECT_PLAN.md](GROUP_SPACE_PROJECT_PLAN.md)** — extends existing `group_space` app (not multi-group academic membership).

**Product rules (agreed)** — details in plan doc:

- Nav / page: **Чат** (not “Group”)
- Picker: academic **group name** first (auto), then custom spaces by **`created_at`**; custom label = **`title`** (create/edit)
- Members: students from **any cohort**; **any teacher** can be added
- **Admin**: sees and manages **all** project spaces (no membership required)
- Academic `User.group` unchanged; project spaces do not affect tasks/goals/workflows

| Feature | Status |
|---------|--------|
| `ProjectSpace` + membership (staff-managed) | Planned |
| Nav label **Чат** + unified feed / space picker | Planned |
| Cross-cohort students + any teacher in space | Planned |
| Admin full project-space management | Planned |
| Shared chat partials (composer, bubbles, HTMX) | Planned |
| System Resources container per project + chat sync | Planned |
| Staff CRUD: create, edit title, members, archive | Planned |
| Resources UI: Project tab | Planned |

---

## Entity → Resources container link

Plan: **[ENTITY_RESOURCE_CONTAINER_PLAN.md](ENTITY_RESOURCE_CONTAINER_PLAN.md)**

**Product rules (agreed):** link existing **thematic** (Themes) or create new theme — no new type; cohort/group: all assignees open via entity (not group-only access); title `Materials: {entity.title}` editable; no system group tile in picker.

| Feature | Status |
|---------|--------|
| Entity FK → thematic `ResourceContainer` | Planned |
| `can_view_container` via entity assignees (cohort-safe) | Planned |
| Create/edit: pick or create thematic on entity forms | Planned |
| Detail: **Open materials** for assignees | Planned |
| Student personal task/goal → Personal container | Planned |

---

## Infrastructure & scale (reference, not feature plans)

- Object storage / media scaling: [SCALING_ROADMAP.md](../SCALING_ROADMAP.md)
- Production go-live: [PRODUCTION_CHECKLIST.md](../PRODUCTION_CHECKLIST.md)

---

## Admin/platform updates (implemented)

These are now implemented in code and no longer tracked as separate plan docs:

| Capability | Status |
|------------|--------|
| Administration dropdown + current item structure | Done |
| Custom Django Admin index grouping (logs/core/scheduling/modules/apps) | Done |
| App module toggles (`IntegratedModule`) + module gate/stub pages | Done |
| Bug reports app + admin inbox + email flow | Done |

---

## Suggested priority (product)

1. Finish Beat + env for existing Slack digest  
2. Scheduling MVP (publish + entity reminders) on one entity (Task)  
3. **Project spaces** (Phases 0–2 in [GROUP_SPACE_PROJECT_PLAN.md](GROUP_SPACE_PROJECT_PLAN.md))  
4. **Entity → Resources container link** ([ENTITY_RESOURCE_CONTAINER_PLAN.md](ENTITY_RESOURCE_CONTAINER_PLAN.md))  
5. Personal Slack OAuth + dispatcher  
6. Group chat ↔ Slack sync
