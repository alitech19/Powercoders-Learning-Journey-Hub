# Admin Panel & Administration UI Restructure

## Goal

1. **Web UI (PowerHUB nav):** One **Administration** entry for `Role.ADMIN` only — dropdown with **Django admin** and **existing admin-only PowerHUB pages** (cohorts/groups, bulk user import, future bug inbox). **Shared** staff tools (user list, create user, student progress) stay on **dashboard + staff nav** like teachers — not in this menu. Remove the loose top-right “Admin” text link.
2. **Django admin (`/admin/`):** Reorganize the index — **group by product area / app**, not default alphabetical app list. Order: **logs & ops → core (non-toggleable) → module toggles → per-app model groups** (workflows, goals, tasks, …).

Documentation only unless implementation is requested separately.

---

## Product decisions (agreed)

| Rule | Detail |
|------|--------|
| **Who sees Administration nav** | **`Role.ADMIN`** and superuser only — not teachers |
| **Dropdown scope** | Django admin + PowerHUB URLs guarded by **`@admin_required`** on the main screen (no teacher access) |
| **In dropdown (existing)** | **Адмін-панель** · **Когорти та групи** (`accounts:cohort_list`) · **Масовий імпорт** (`accounts:user_import`) |
| **In dropdown (planned)** | **Баг-репорти** inbox when [BUG_BOUNTY_PLAN.md](BUG_BOUNTY_PLAN.md) ships |
| **In dropdown (planned)** | **Сховище файлів** (`accounts:storage_settings`) — [GOOGLE_DRIVE_INTEGRATION_PLAN.md](GOOGLE_DRIVE_INTEGRATION_PLAN.md) |
| **Not in dropdown** | User list, create user, student progress (teachers use the same pages) · audit log / module toggles (Django admin only) |
| **Django admin access** | Admin + superuser only (`is_staff` / `/admin/`) — audit log, Celery Beat, module toggles, model CRUD live **here**, not in the web dropdown |
| **Teachers** | No Administration dropdown; same product nav groups as today/planned |
| **Language** | Nav label: **Адміністрування** |

---

## Part A — Web UI: Administration dropdown

### Current state

- `base.html`: plain link `Admin` → `admin:index` (top-right).
- Admin **dashboard** “Management” grid: cohorts, users, progress, audit log — **correct place** for shared staff tools; keep it.
- Planned: [BUG_BOUNTY_PLAN.md](BUG_BOUNTY_PLAN.md) inbox at `/bugs/inbox/` — **admin-only web UI** → belongs in dropdown.
- [APP_MODULE_TOGGLES_PLAN.md](APP_MODULE_TOGGLES_PLAN.md) — toggles **only in Django admin**, not dropdown.

### Target nav (admin user)

```text
[ Logo ]  Learning ▾  Wellbeing ▾  Чат  Resources  …staff nav as teachers…  [🔔]  [Адміністрування ▾]  [Avatar ▾]
```

**Адміністрування ▾** — flat list, no sections (v1):

| Label (UK) | `url_name` | View | Access today |
|------------|------------|------|----------------|
| **Адмін-панель** | `admin:index` | Django admin | `admin` / superuser |
| **Когорти та групи** | `accounts:cohort_list` | Cohorts & groups CRUD, assign students | `@admin_required` |
| **Масовий імпорт користувачів** | `accounts:user_import` | CSV bulk create users | `@admin_required` |
| **Баг-репорти** | `bug_reports:inbox` (planned) | Admin triage inbox | admin only |

Existing routes: `/accounts/cohorts/`, `/accounts/users/import/` ([`management_views.py`](../../backend/accounts/management_views.py)).

**Not in dropdown** (admins also use dashboard / staff nav — same as teachers):

| Tool | Where |
|------|--------|
| Users / create user | `accounts:user_list`, `accounts:user_create` — `@teacher_or_admin_required` |
| Student progress | `accounts:student_progress` — `@teacher_or_admin_required` |
| Audit log, app toggles, model repair | Django admin (Part B grouping) |

Add dropdown entries when a **new** top-level admin-only PowerHUB page appears (not for every nested `@admin_required` action URL).

### Implementation sketch

| Piece | Location |
|-------|----------|
| `ADMIN_NAV_ITEMS` | `config/admin_menu.py` — fixed list above; gate on `user_is_admin`; omit bug item if module disabled |
| Context processor | `admin_nav_items(request)` → `[]` for non-admins |
| Template partial | `includes/_admin_nav_dropdown.html` in `base.html` |
| Dashboard | **Unchanged** Management block — primary hub for users/cohorts/progress |

Remove from navbar:

```html
<a href="{% url 'admin:index' %}">Admin</a>
```

Replace with **Адміністрування ▾**.

### Permission guard

All dropdown targets use existing `@admin_required` (or staff for Django admin). Teachers never see the menu.

---

## Part B — Django admin: custom grouping

### Problem

Default `admin/index` lists apps **alphabetically** (`accounts`, `cohorts`, `goals`, `journal`, …). Hard for admins to find workflows vs tasks or logs first.

### Solution: custom `AdminSite`

```text
config/
  admin_site.py      # PowerHubAdminSite(AdminSite)
  admin_registry.py  # explicit model registration order (optional)
```

`urls.py`:

```python
from config.admin_site import powerhub_admin_site
path('admin/', powerhub_admin_site.urls),
```

Override **`get_app_list(request)`** (and optionally **`index_template`**) to emit **sections**:

### Section order on admin home

#### 1) Logs & operations (first)

| Group label | Models / apps |
|-------------|----------------|
| **Logs** | `accounts.AuditLog` |
| **Scheduling** | `django_celery_beat` — Periodic tasks, Crontab, Intervals, Solar (collapse “intervals” if noisy) |
| **Security** (optional) | `axes` access attempts; `otp_totp` / `otp_static` if admins need device resets |

#### 2) Core platform (always on — not in module toggles)

| Group label | Models |
|-------------|--------|
| **Users & access** | `accounts.User`, `accounts.Notification` |
| **Cohorts & groups** | `cohorts.Cohort`, `cohorts.Group` |
| **Feedback** | `feedback.FeedbackEntry` |
| **Google storage** | `GoogleWorkspaceStorageConfig` (singleton — Shared drive + OAuth creds) |

#### 3) Module switches

| Group label | Models |
|-------------|--------|
| **App modules** | `config.IntegratedModule` (or `accounts.IntegratedModule`) — enable/disable apps per [APP_MODULE_TOGGLES_PLAN.md](APP_MODULE_TOGGLES_PLAN.md) |

When a module is **disabled**, models may still appear in admin for data repair (per toggles plan) — optional filter gray-out in custom index v2.

#### 4) Learning apps (grouped by product app)

Each block = one product name; models listed together (not scattered alphabetically).

| Group label | Models (typical) |
|-------------|------------------|
| **Workflows** | Workflow, WorkflowStep, WorkflowEnrollment, StepCompletion |
| **Tasks** | Task, TaskEnrollment, Subtask, SubtaskCompletion, TaskUpdate, TaskComment |
| **Goals** | Goal, GoalEnrollment, Milestone, MilestoneCompletion |
| **Reflections** | Reflection |
| **Journal** | JournalEntry |
| **Habits** | Habit, HabitLog |
| **Group space (Чат)** | GroupSpace, Post, Comment |
| **Resources** | ResourceContainer, ResourceItem |
| **Bug reports** | BugReport, BugReportMessage — when app exists |

#### 5) Auth / Django internals (last, collapsed)

| Group label | Notes |
|-------------|--------|
| **Authentication** | Only if needed; `AuthGroup` already unregistered |

### Custom index template (optional polish)

`templates/admin/powerhub_index.html` — extends admin index with section headings and cards per group (Django 4+ `app_list` in template).

### Model `Meta` / `verbose_name_plural`

Ensure each model has clear **`verbose_name_plural`** under its app — grouping uses app labels + model class names from registry.

### Register all models on custom site

Move `@admin.register` to use `powerhub_admin_site.register(...)` **or** import apps in `admin_site.py` after site creation — migration path:

1. Subclass site + override `get_app_list`
2. Keep existing `admin.register` autodiscover — `admin.autodiscover()` then re-hook to custom site (standard Django pattern)

---

## `get_app_list` algorithm (pseudo)

```python
SECTIONS = [
  {'title': 'Logs & operations', 'apps': ['accounts_audit', 'django_celery_beat', 'axes', ...]},
  {'title': 'Core platform', 'apps': ['accounts', 'cohorts', 'feedback']},
  {'title': 'App modules', 'apps': ['config']},
  {'title': 'Workflows', 'apps': ['workflows']},
  ...
]
# Map Django's built-in app_list into sections; append unmapped to "Other"
```

Filter: user must be staff; non-superuser admin sees same layout.

---

## Relationship to other plans

| Plan | Link |
|------|------|
| [APP_MODULE_TOGGLES_PLAN.md](APP_MODULE_TOGGLES_PLAN.md) | **App modules** section in Django admin |
| [BUG_BOUNTY_PLAN.md](BUG_BOUNTY_PLAN.md) | **Second** dropdown item (inbox); models also in Django admin |
| Product nav (`config/nav.py`) | **Staff nav** (users, progress); **Адміністрування ▾** = Django admin + admin-only setup pages |
| [GROUP_SPACE_PROJECT_PLAN.md](GROUP_SPACE_PROJECT_PLAN.md) | Future **ProjectSpace** models under Group space or new admin group |

---

## Implementation phases

### Phase 1 — Web Administration dropdown

- [ ] `config/admin_menu.py` — Django admin, `cohort_list`, `user_import`, + bug inbox when ready
- [ ] `_admin_nav_dropdown.html` in `base.html`
- [ ] Remove old Admin link
- [ ] Align product **staff nav** so admins see users/progress like teachers (cohorts stay dashboard or staff nav)

### Phase 2 — Custom AdminSite + ordered index

- [ ] `PowerHubAdminSite` + wire `urls.py`
- [ ] `get_app_list` section ordering
- [ ] Smoke test: admin login, all models reachable

### Phase 3 — Template polish & docs

- [ ] Custom `powerhub_index.html` section headers
- [ ] `info/topics` admin help for new menu
- [ ] Update [dashboard.md](../../backend/info/topics/dashboard.md) admin section

---

## Files to touch

| Area | Files |
|------|--------|
| Config | `config/admin_site.py`, `config/admin_menu.py`, `config/urls.py`, `context_processors.py` |
| Templates | `base.html`, `includes/_admin_nav_dropdown.html`, optional `admin/powerhub_index.html` |
| Each `*/admin.py` | Optionally switch to `powerhub_admin_site.register` |
| Dashboard | `dashboard/dashboard.html` (admin) |
| Docs | `TODO.md`, `info/registry.py` if admin help page added |

---

## Success criteria

- [ ] **Адміністрування ▾**: Django admin, cohorts/groups, bulk import, bug inbox (when live)
- [ ] Users & student progress via **dashboard / staff nav** — not duplicated in administration menu
- [ ] Teacher does **not** see Administration dropdown
- [ ] Django admin home shows **Logs first**, then Users/Cohorts/Feedback, then **App modules**, then Workflows / Tasks / Goals / … blocks
- [ ] No reliance on alphabetical app order for daily ops

---

## Open questions (optional)

1. **Ukrainian-only** labels in dropdown vs EN? (Proposal: **UK** — «Адмін-панель», «Когорти та групи», «Масовий імпорт користувачів», «Баг-репорти».)
2. Include **Celery Beat** under Logs for all admins or superuser only? (Proposal: all admins — Django admin only.)
