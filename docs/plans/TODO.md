# TODO — Potential features & plans

Index of planned capabilities. Implementation details live in the linked docs.

Deploy and Beat setup: [DEPLOY.md](../DEPLOY.md) · Local: [SETUP.md](../SETUP.md)

---

## Near-term ops (no separate plan)

- [ ] Register **weekly missing-reflections** in Django admin → **Periodic tasks** (`accounts.tasks.notify_missing_reflections`)
- [ ] Production env: `SLACK_WEBHOOK_URL`, `SITE_URL` (global staff webhook — see [SLACK_INTEGRATION_PLAN.md](SLACK_INTEGRATION_PLAN.md))

Beat admin: http://localhost:8000/admin/django_celery_beat/

---

## Slack integration

Plan: **[SLACK_INTEGRATION_PLAN.md](SLACK_INTEGRATION_PLAN.md)**

| Feature | Status |
|---------|--------|
| Global staff webhook (feedback, new user, missing reflections digest) | Partially done |
| Per-user Slack OAuth (connect / disconnect) | Planned |
| Personal notification settings (in-app / email / Slack toggles) | Planned |
| Unified notification dispatcher (dedupe, delivery log) | Planned |
| Slack DM: feedback, new task/goal/workflow, deadline reminders | Planned |
| Group chat → Slack channel sync (one-way) | Planned |
| Group chat ↔ Slack (two-way) + thread → flat reply links | Planned |

---

## Scheduling & reminders

Plan: **[SCHEDULING_AND_REMINDERS_PLAN.md](SCHEDULING_AND_REMINDERS_PLAN.md)**

| Feature | Status |
|---------|--------|
| Scheduled publish (`publish_at`) for task / goal / workflow | Planned |
| Entity deadline reminders (24h, 2h, overdue) | Planned |
| Standalone reminders — one-time (staff) | Planned |
| Standalone reminders — recurring (daily / weekly / monthly) | Planned |
| Central scheduler (`ScheduledAction`) + delivery log | Planned |
| Rate limit: 1 batch/min, jitter, multi-message batches | Planned |
| UI: Schedule block on entity forms; staff **Automation / Reminders** page | Planned |

Timezone: **Europe/Zurich** (all schedules).

---

## Google Drive & resources storage

Plan: **[GOOGLE_DRIVE_INTEGRATION_PLAN.md](GOOGLE_DRIVE_INTEGRATION_PLAN.md)** (per-user Drive; local `MEDIA_ROOT` until then)

| Feature | Status |
|---------|--------|
| Chat file uploads → uploader’s Drive (not `MEDIA_ROOT`) | Planned |
| Auto folder `PowerHUB/Groups/{group}/` per user | Planned |
| Auto share **anyone with the link** on upload | Planned |
| Google OAuth (org email must match `User.email`) | Planned |
| Resources tiles use `webViewLink`; open in browser Google session | Planned |
| Legacy local `media/group_files/` (read-only / migration) | Current → sunset |

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

## UI & layout (teacher feedback)

Plan: **[UI_LAYOUT_IMPROVEMENT_PLAN.md](UI_LAYOUT_IMPROVEMENT_PLAN.md)**

**Product rules (agreed):** volumetric icons only · nav **Learning** (Workflows, Tasks, Goals, Habits) · **Wellbeing** (Reflections, Journal) · **Чат** · Resources · create (e.g. New Task) on **list card**, not page header

| Feature | Status |
|---------|--------|
| Nav: 4 groups (Learning + Habits · Wellbeing · Чат · Resources) | Planned |
| **Volumetric** icons only app-wide (one tile component) | Planned |
| Help (ⓘ) smaller, inline after page title | Planned |
| Purpose subtitle on every tool page | Planned |
| Create CTA top-right in list card (not page header) | Planned |
| Avatar dropdown: name, Profile, Log out | Planned |

---

## App module toggles (admin)

Plan: **[APP_MODULE_TOGGLES_PLAN.md](APP_MODULE_TOGGLES_PLAN.md)**

**Product rules:** toggles **only in Django admin**, **admin role only**; disabled → no nav/dashboard/share tabs; chat history unchanged; files/links in chat OK, no Resources sync if resources off; app URLs → **stub** (admin sees enable hint); friendly 404/403/500 pages.

| Feature | Status |
|---------|--------|
| `IntegratedModule` + Django admin (admin-only) | Planned |
| Nav, dashboard, chat share panel filtered | Planned |
| Stub pages + middleware (not bare 404) | Planned |
| Friendly error pages (404/403/500) | Planned |
| Chat: skip Resources sync; task links → stub when tasks off | Planned |
| Single release (visibility + gates together) | Planned |

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

## Tasks — list status bug & full subtasks

Plan: **[TASKS_STATUS_AND_SUBTASKS_PLAN.md](TASKS_STATUS_AND_SUBTASKS_PLAN.md)**

| Feature | Status |
|---------|--------|
| **Bug:** student status buttons on Tasks list (To do / Doing / Done / Blocked) | Planned |
| Subtasks: task-like fields (status, priority, due, description) | Planned |
| `SubtaskEnrollment` replaces boolean completion | Planned |
| UI: subtask status pills, not milestone checkboxes | Planned |
| Goals milestones unchanged | — |

---

## Infrastructure & scale (reference, not feature plans)

- Object storage / media scaling: [SCALING_ROADMAP.md](../SCALING_ROADMAP.md)
- Production go-live: [PRODUCTION_CHECKLIST.md](../PRODUCTION_CHECKLIST.md)

---

## Admin restructure (web + Django admin)

Plan: **[ADMIN_RESTRUCTURE_PLAN.md](ADMIN_RESTRUCTURE_PLAN.md)**

| Feature | Status |
|---------|--------|
| Nav **Адміністрування ▾**: Django admin, cohorts/groups, bulk import, bug inbox | Planned |
| Users/progress via dashboard + staff nav (not in administration dropdown) | Planned |
| Custom `AdminSite` — grouped index (logs → core → toggles → apps) | Planned |
| Remove loose navbar “Admin” link | Planned |

---

## Bug bounty / bug reports

Plan: **[BUG_BOUNTY_PLAN.md](BUG_BOUNTY_PLAN.md)** — toggleable app `bug_reports`.

| Feature | Status |
|---------|--------|
| Crosshair button next to ⓘ (per-page URL) | Planned |
| Submit form + DB storage | Planned |
| Admin inbox: take / close / reject / reopen + assignee visible | Planned |
| Admin reply + emails (reporter ack, admins new, reply) | Planned |
| Django admin + `IntegratedModule` toggle | Planned |

---

## Suggested priority (product)

1. **Tasks list status bug** ([TASKS_STATUS_AND_SUBTASKS_PLAN.md](TASKS_STATUS_AND_SUBTASKS_PLAN.md) Phase 1) — small fix, first  
2. Finish Beat + env for existing Slack digest  
3. Scheduling MVP (publish + entity reminders) on one entity (Task)  
4. Google Drive chat upload (Phase 0–1)  
5. **UI & layout** ([UI_LAYOUT_IMPROVEMENT_PLAN.md](UI_LAYOUT_IMPROVEMENT_PLAN.md)) — quick win; aligns with bug button next to ⓘ  
5b. **Admin restructure** ([ADMIN_RESTRUCTURE_PLAN.md](ADMIN_RESTRUCTURE_PLAN.md)) — can ship with UI nav (dropdown + Django admin grouping)  
6. **Bug reports app** ([BUG_BOUNTY_PLAN.md](BUG_BOUNTY_PLAN.md)) — after UI header row or in parallel  
7. **App module toggles** ([APP_MODULE_TOGGLES_PLAN.md](APP_MODULE_TOGGLES_PLAN.md)) — include `bug_reports` slug  
8. **Full subtasks** (Phase 2–3 in [TASKS_STATUS_AND_SUBTASKS_PLAN.md](TASKS_STATUS_AND_SUBTASKS_PLAN.md))  
9. **Project spaces** (Phases 0–2 in [GROUP_SPACE_PROJECT_PLAN.md](GROUP_SPACE_PROJECT_PLAN.md))  
10. Personal Slack OAuth + dispatcher  
11. Group chat ↔ Slack sync  

Adjust order with team/IT (Workspace sharing policy blocks Drive link sharing if misconfigured).
