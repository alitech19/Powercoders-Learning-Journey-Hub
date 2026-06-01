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

| Step | Detail | Status |
|------|--------|--------|
| ~~Role decorators~~ | `admin_required`, `teacher_or_admin_required`, `student_required` | Done — `accounts/decorators.py` |
| ~~User management~~ | List, create, CSV import, deactivate / reactivate / admin delete | Done — `accounts/management_views.py`, `/accounts/users/` |
| ~~Student oversight~~ | `student_progress`, `student_detail` (shared journal/goals/reflections) | Done — powers teacher dashboard preview |
| ~~Cohort / group UI~~ | CRUD, assign teachers, bulk assign students (US-39) | Done — `/accounts/cohorts/` |
| ~~GDPR~~ | `data_export` (full Markdown), `delete_own_account` | Done — profile UI |
| ~~Notification centre~~ | `Notification` model + in-app list + nav bell | Done |
| Audit log (UI) | Optional staff page | **Admin only** — `AuditLog` + middleware exist |

**Integration today:** staff workflows in app UI; Django admin still available for edge cases.

---

## 3. Notifications and integrations

| Step | Detail | Ali reference |
|------|--------|---------------|
| ~~Welcome email~~ | On **user create** and **CSV import** | Done — `accounts/emails.py` |
| ~~Slack — new users~~ | Webhook when users are created or imported | Done — `accounts/slack.py` (`SLACK_WEBHOOK_URL`) |
| ~~Slack — feedback~~ | Webhook when staff leaves feedback | Done — via `feedback` app |
| Slack — reflections | Missing weekly reflections digest | `accounts.tasks.notify_missing_reflections` — register in Beat ([TODO.md](TODO.md)) |
| ~~Email on feedback~~ | Notify students when staff leave feedback | Done — generic **`feedback`** + `email_notifications_enabled` |

**Integration today:** welcome email + Slack on create/import; in-app + email on staff feedback; Celery task ready — configure periodic schedule in admin when enabling Slack in production.

---

## 4. API (optional)

| Step | Detail |
|------|--------|
| Django Ninja scaffold | Ali exposes `GET /api/health` via Ninja; integration has `GET /health/` only — add Ninja only if we want a versioned API surface |

---

## 5. Automated tests

**Guide:** [TESTING.md](../TESTING.md). **Done:** all business apps (`cohorts` … `info`). Goal: **as full coverage as practical** without brittle HTML snapshots. Prefer behaviour, permissions, and data invariants. **Rewrite** for integration models — do not copy Ali `tracker` tests.

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

Run sequentially, e.g. `test cohorts accounts`, then `tasks goals workflows`, etc. Coverage: see [TESTING.md](../TESTING.md) — `.coveragerc` omits migrations/admin/urls; **views/forms** still need tests for a high honest %.

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
