# Integration — remaining work

Compared to **`origin/Ali`** (`42f74c2`). On **`integration`**, customer-facing apps are in place: Workflows → Resources (nav), role-based **dashboard** at `/`, contextual **info** help (ⓘ), generic **feedback**, **tasks** (not `tracker`), **resources** sync from group chat, embedded wellbeing in **reflections**.

Below is only what is **still to do**. Scheduled **task code**: **[TODO.md](TODO.md)**. Port or rewrite from Ali where noted — **do not** merge Ali `goals/`, `workflows/`, or `tracker/` as-is; integration architecture is ahead there.

---

## 1. CI and Docker

| Step | Detail | Notes |
|------|--------|--------|
| ~~**Dev superuser guard**~~ | `CREATE_DEV_SUPERUSER=true` only | Done — `docker-compose.yml`, `.env.example` |
| ~~**GitHub Actions**~~ | PG 17 + Redis, `migrate`, `migrate --check`, tests per app | Done — `.github/workflows/ci.yml` |
| ~~**Celery beat (infra)**~~ | `beat` service + `django-celery-beat` | Done — schedules via admin when tasks exist |
| ~~pgvector~~ | — | **Won’t do** — keep `postgres:17-alpine` |

**§1 open:** automated tests (see §5). **Scheduled task implementations:** [TODO.md](TODO.md).

---

## 2. Accounts and admin UI

| Step | Detail | Ali reference |
|------|--------|---------------|
| Role decorators | `admin_required`, `teacher_or_admin_required`, `student_required` | `accounts/decorators.py` |
| User management | List, create, CSV import, deactivate / reactivate | `accounts/views.py`, templates |
| Student oversight | `student_detail`, `student_progress` | same |
| Cohort / group UI | CRUD + assign teachers + **bulk assign students to group** (US-39) | same (not only Django admin) |
| GDPR | `data_export`, self-service `delete_own_account`, admin `user_delete_account` | same |
| Notification centre | `Notification` model, list + mark read, tie to email prefs | migration `0008_add_notifications`, views/templates |
| Audit log (UI) | Admin-facing audit log page | `audit_log` view — model + `AuditLoggingMiddleware` already exist on integration |

**Integration today:** profile, welcome, privacy policy, password-change gate, 2FA, dev quick-login, `AuditLog` in admin only; cohorts/groups via **admin** only.

---

## 3. Notifications and integrations

| Step | Detail | Ali reference |
|------|--------|---------------|
| Slack | Webhooks for feedback, new users, missing weekly reflections | `accounts/slack.py` |
| Celery task | `notify_missing_reflections` on a schedule | [TODO.md](TODO.md) — Beat infra ready |
| Email on feedback | Notify students when staff leave feedback | `accounts/emails.py` — wire to generic **`feedback`** app / enrollments, not legacy `GoalComment` |

**Integration today:** `email_notifications_enabled` on `User`; no Slack, no outbound feedback email, no scheduled reflection reminders.

---

## 4. API (optional)

| Step | Detail |
|------|--------|
| Django Ninja scaffold | Ali exposes `GET /api/health` via Ninja; integration has `GET /health/` only — add Ninja only if we want a versioned API surface |

---

## 5. Automated tests

Integration has **no** `tests/` modules yet. Goal: **as full coverage as practical** without brittle HTML snapshots. Prefer behaviour, permissions, and data invariants. **Rewrite** for integration models — do not copy Ali `tracker` tests.

### Layout (per Django app)

```
backend/<app>/tests/
  test_models.py
  test_services.py
  test_permissions.py
  test_views.py
  test_signals.py   # e.g. resources ← group_space
```

Add shared factories in `backend/test_utils/` (`make_student`, `make_teacher`, `make_cohort`, `make_group`, `login_as`).

**Cross-app:** e.g. group post → Resources item, feedback on goals/reflections, dashboard aggregates — `dashboard/tests/` or `backend/tests/`.

### What to test (priority)

| Layer | Examples |
|-------|----------|
| Models | `clean()`, progress %, due dates |
| Services | task visibility, goal enrollments, resources sync, feedback registry |
| Permissions | role matrix, wrong group denied |
| Views | HTTP, redirects, messages |
| Celery | eager + mock Slack (with [TODO.md](TODO.md) tasks) |

### Build order

1. `cohorts` + `accounts` → 2. `tasks` → 3. `goals` → 4. `feedback` + one consumer → 5. `workflows`, `reflections`, `journal`, `habits` → 6. `group_space` + `resources` → 7. `dashboard` → 8. `info`

### CI

Run sequentially, e.g. `test cohorts accounts`, then `tasks goals workflows`, etc. Optional later: `coverage` with threshold.

### Test settings

`CELERY_TASK_ALWAYS_EAGER`, locmem email, Redis service in CI (sessions match prod), disable axes if it blocks logins.

---

## 6. Operations documentation

| Step | Detail | Ali reference |
|------|--------|---------------|
| Runbooks | Incident response, scaling roadmap | `docs/INCIDENT_RESPONSE.md`, `docs/SCALING_ROADMAP.md` |
| UX process | Usability testing notes | `docs/USABILITY_TESTING.md` |

---

## 7. Pre-production hardening

Follow [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md): remove dev seed, `dev_quick_login`, docker seed commands, etc. Overlaps §1 dev superuser guard.

---

## Explicitly out of scope

- **Cohort default tasks** (US-58) — teachers assign tasks; enroll on existing tasks instead.
- **Ali `goals` / `workflows` / `tracker`** code paths — take ideas/tests only after adapting to integration.
- Separate **`wellbeing`** app — wellbeing stays inside **reflections** on integration.

---

## Reference (no open tasks)

- Resource files: [RESOURCE_FILE_STORAGE.md](RESOURCE_FILE_STORAGE.md) — group uploads (Option 1) implemented on integration.
- Deploy: [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)
