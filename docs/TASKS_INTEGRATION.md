# Tasks app — integration plan & context

**Branch:** `integration`  
**Status:** implemented (integration branch)  
**Full spec for agents/devs** — read this before implementing `backend/tasks/`.

Related: [APPS_ROADMAP.md](APPS_ROADMAP.md) · [AUTH_ROADMAP.md](AUTH_ROADMAP.md)

---

## 1. Integration branch state (done before Tasks)

| App | Package | Pattern |
|-----|---------|---------|
| Workflows | `workflows/` | Template + enrollments; shared/individual progress; private staff drafts |
| Goals | `goals/` | Template + `GoalEnrollment` + `MilestoneCompletion`; staff bulk = 1 list row |
| Feedback | `feedback/` | Generic `FeedbackEntry` (Generic FK); per-app hooks; admin only, not in nav |
| Cohorts | `cohorts/` | Shared `cohorts/permissions.py` for teacher scope |

**Do not git-merge** `origin/Ali` or `origin/django-test` into `integration`. Port selected files only.

---

## 2. Tasks — decisions (fixed)

| Topic | Decision |
|-------|----------|
| Django app name | **`tasks`** (not `tracker`) |
| Nav label | **Tasks** |
| URL prefix | `/tasks/` · namespace `tasks:` |
| Model base | **`origin/django-test:tracker/models.py`** — no TaskBoard |
| Enrollment | **Yes** for individual assign; **no** for group shared |
| UI | **`origin/Ali:frontend/templates/tracker/`** — list filters, sort, pagination, HTMX status |
| Bulk assign UI | **integration goals form** — Alpine cohort/group/student picker |
| Staff list | **1 task → N students** (individual) or **1 group task** (shared) |
| Staff detail | Enrollment table (individual) or single shared status (group) |
| Permissions helpers | **Import** from `cohorts/permissions.py` — never duplicate |
| App permissions | **`tasks/permissions.py`** — all task/enrollment rules |
| Staff feedback | **`feedback` app** on `TaskEnrollment` (like goals) |
| TaskComment / TaskUpdate | FK → **`TaskEnrollment`** (individual tasks) |
| Template subtasks | **`Subtask` on Task** + **`SubtaskCompletion` on enrollment** |
| Feature toggles | **`allow_updates`**, **`allow_comments`**, **`allow_subtasks`** on create/edit |

### Visibility (staff-assigned — like goals/workflows)

| `visibility` | Student | In-scope teacher | Admin |
|--------------|---------|------------------|-------|
| **shared** | enrolled / assignee sees | yes | yes |
| **private** | **hidden** (draft) | yes | yes |

Student **personal** private tasks: only owner (django-test rule).

### Feature toggles

Three independent booleans on **Task** (create/edit). When `False`, **hide the whole section** on detail (existing data stays in DB but is not shown).

| Field | When `False` |
|-------|----------------|
| `allow_updates` | Hide updates section (**no old, no new**) |
| `allow_comments` | Hide comments section (**no old, no new**) |
| `allow_subtasks` | Hide subtasks/checklist on detail for viewers; block participant-added subtasks |

**Staff edit form:** may still manage template subtasks via `sync_subtasks` even when `allow_subtasks=False` (checklist hidden from students until re-enabled).

Staff create defaults: **all toggles ON**.

Staff-assigned: student **cannot** edit title/description (status / checklist / updates per toggles only).

---

## 3. Target architecture

```
Task
  assignee_type: user | group | cohort
  progress_mode: individual | shared   ← auto shared when assignee_type=group
  visibility: private | shared         ← staff draft vs published (goals/workflows)
  allow_updates, allow_comments, allow_subtasks
  status, completed_at                 ← used for shared group tasks (on Task)

TaskEnrollment                       ← individual mode only (incl. personal task)
  student, status, completed_at

Subtask                              ← template checklist (staff sync)
SubtaskCompletion                    ← per enrollment

TaskUpdate, TaskComment              ← FK TaskEnrollment
```

### Task kinds

| Kind | Shape |
|------|--------|
| **Personal** (student) | `Task` + `assignee_user=self` + **always 1 `TaskEnrollment`** · visibility **private** (only me) or **shared** (teachers in scope) |
| **Staff bulk → students** | `assignee_type=user`, `progress_mode=individual`, 1 Task + N enrollments |
| **Staff → group** | `assignee_type=group`, **`progress_mode=shared`**, status on Task, **no enrollments** |
| **Staff bulk → cohort students** | pick students → individual + enrollments (like goals) |
| **Late joiner** | Teacher **adds `TaskEnrollment`** to an existing task (no auto-defaults) |

`assignee_type=group` ⇒ shared progress for whole group (one status, one task row).

**No auto-created tasks.** All assignments are **teacher-created**. Ali `CohortDefaultTask` / signals — **out of scope**.

---

## 4. Permissions layout

```
cohorts/permissions.py     shared role/scope helpers
        ↓
tasks/permissions.py       can_view_task, can_view_enrollment, can_manage_task,
                           can_change_status, can_add_update, can_comment, …
                           staff private draft rules (mirror goals/workflows)
        ↓
tasks/feedback_handlers.py → register TaskEnrollment on feedback registry
tasks/services.py          bulk create, sync_subtasks, scope validation
```

Reference: `goals/permissions.py`, `goals/feedback_handlers.py`, `workflows/permissions.py`.

---

## 5. Source map

| Need | Source |
|------|--------|
| Task, Update, Comment models | django-test `tracker/models.py` |
| Owner/assignee rules | django-test `permissions.py` + goals/workflows visibility |
| Comment tree | django-test `services.py` |
| Bulk create / sync | integration `goals/services.py` |
| List UI | Ali `frontend/templates/tracker/` → `tasks/` |
| Staff tables | goals `_staff_enrollments.html` |
| Bulk form | goals `goal_form.html` |
| Feedback hooks | goals `feedback_handlers.py` |

**Do not port:** TaskBoard, Ali tracker models, django-test views without enrollment.

---

## 6. PR plan

| PR | Scope |
|----|--------|
| **PR1** | Models, migrations, admin, toggles, `progress_mode` |
| **PR2** | `permissions.py`, `services.py`, tests |
| **PR3** | Student personal CRUD, list UI (Ali), nav |
| **PR4** | Staff bulk (individual) + group shared + visibility + **add enrollment** to existing task |
| **PR5** | Subtasks, updates, comments (gated by toggles) + **feedback app** |
| **PR6** | Polish, tests, roadmap Done |
| **PR7** | Optional backports: CI, decorators, Slack |

---

## 7. Resolved decisions (2026-05-30)

| # | Decision |
|---|----------|
| Q1 | Personal task → **always `TaskEnrollment`** |
| Q2 | **`assignee_type=group` ⇒ `progress_mode=shared`** (v1) |
| Q3 | `allow_updates=False` → **hide all updates** (old + new) |
| Q3b | `allow_comments=False` → **hide all comments** (old + new) |
| Q4 | `allow_subtasks=False` → hide subtasks on detail; staff **can** still `sync_subtasks` on edit |
| Q5 | Staff-assigned → student **cannot** edit title/description |
| Q6 | Staff **private** → hidden from students; **in-scope teachers + admin** see (goals/workflows) |
| Q7 | Staff create → **all toggles default ON** |
| Q8 | Staff feedback → **`feedback` app** on enrollment (PR5) |
| Q9 | Group assign → **shared only**, no per-student enrollments |
| Q10 | **No `CohortDefaultTask`** — no auto tasks; teachers assign; late join = new enrollment on existing task |

---

## 8. Out of scope

- **`CohortDefaultTask`** (Ali US-58) — not porting; no signals, no admin default checklist
- Auto-provision tasks on cohort join
- New student coverage: teacher **enrolls them on existing tasks** manually (staff detail / edit assignment — like workflows add enrollment)

---

## 9. Ali branch — do not merge

Cherry-pick infra/docs only (APPS_ROADMAP B1–B15). Do not merge Ali `goals/` / `workflows/` / `tracker/` code.

---

## 10. Changelog

| Date | Change |
|------|--------|
| 2026-05-30 | Initial plan |
| 2026-05-30 | Q1–Q9 resolved; CohortDefaultTask explained + deferred |
| 2026-05-30 | No CohortDefaultTask; toggles hide old comments too; add enrollment for late join |
