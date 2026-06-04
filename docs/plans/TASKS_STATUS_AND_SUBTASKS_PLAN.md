# Tasks — List Status Bug & Full Subtasks

## Goal

1. **Bug fix:** Students must see and use **To do / Doing / Blocked / Done** status controls on the **Tasks list** (and keep working on detail).
2. **Product change:** Replace milestone-style subtasks (checkbox done/not done) with **full subtasks** that have task-like attributes, so **Tasks** are clearly different from **Goals** (milestones).

Documentation only unless a separate implementation pass is requested.

---

## Part A — Student status buttons on Tasks tab

### Symptom

Students open **Tasks** list (`tasks:task_list`): status column shows a **read-only badge** only. They cannot change status inline (Doing, To do, Done, Blocked).

On **task detail**, `_task_status_section.html` already supports quick status when `can_edit_status` is true — list view does not.

### Root cause

`_build_list_rows()` sets `can_edit_status` per row (`tasks/views.py`), but `_task_table.html` **never uses it** — only renders a static `<span>` from `row.display_status`.

Permissions are largely correct for enrolled students (`can_change_status` in `tasks/permissions.py`):

- **Individual / cohort** tasks: student with `TaskEnrollment` may change **enrollment.status**.
- **Group shared** tasks: student in `assignee_group` may change **task.status** (shared).

### Fix (v1 — minimal)

| Item | Change |
|------|--------|
| Template | `tasks/_task_table.html` — in Status column: if `row.can_edit_status`, render compact status buttons (same four values as detail), else keep badge |
| HTMX | Reuse `POST tasks:task_quick_status` with `task.pk`; `hx-target` = cell or row fragment |
| Partial | Extract `tasks/_task_status_inline.html` from `_task_status_section.html` (shared by list + detail) |
| Response | `task_quick_status` returns inline partial when `?inline=list` or dedicated `task_list_status` view returning one table cell |
| Group shared | Pass `enrollment=None`; existing view updates `task.status` |
| Enrolled individual/cohort | Pass enrollment; view updates `enrollment.status` |

### Edge cases to test

- [ ] Student, cohort task, enrolled → buttons work on list
- [ ] Student, group shared, same group → buttons update shared status
- [ ] Student, not enrolled → no buttons (badge only)
- [ ] Private task from another student → no content / no buttons
- [ ] Staff list view unchanged (staff edits status on detail per-enrollment table, not required on list v1)

### Success criteria (bug)

- [ ] Student changes status from **list** without opening detail
- [ ] Detail status section still works
- [ ] No regression for teachers/admins

---

## Part B — Subtasks vs Goals milestones

### Today

| | **Goals** | **Tasks (subtasks)** |
|---|-----------|----------------------|
| Child unit | `Milestone` — title only | `Subtask` — title + order |
| Progress | `MilestoneCompletion` (on/off) | `SubtaskCompletion` (on/off) |
| UI | Round checkbox, strike-through | Same pattern in `_subtasks_section.html` |
| Attributes | No status, priority, due date | No status, priority, due date |

Teachers want **Tasks** children to feel like **small tasks**, not clones of goal milestones.

### Target behaviour

Each **subtask** (staff template or student-added) supports:

| Field | Notes |
|-------|--------|
| `title` | Required (existing) |
| `description` | Optional, short |
| `status` | `todo` / `doing` / `blocked` / `done` (same enum as `Task.Status`) |
| `priority` | `low` / `normal` / `high` |
| `due_date` | Optional |
| `order` | Sort order (existing) |

**Per-student progress** (individual / cohort / enrolled work):

- Not a single boolean — each **`TaskEnrollment`** has its own subtask row state via **`SubtaskEnrollment`** (replaces `SubtaskCompletion`).

**Group shared tasks:**

- Subtasks are still defined on the **task template**; status may be **shared on the subtask row** (one status on `Subtask` for whole group) **or** per-enrollment — **recommend per-enrollment** for consistency unless product prefers one group status (open below).

### Data model (proposed)

**Extend `Subtask`:**

```python
class Subtask(models.Model):
    task = models.ForeignKey(Task, ...)
    title = ...
    description = models.TextField(blank=True)
    status = models.CharField(choices=Task.Status.choices, default=TODO)  # used when group-shared single status
    priority = models.CharField(choices=Task.Priority.choices, default=NORMAL)
    due_date = models.DateField(null=True, blank=True)
    order = ...
    added_by = ...  # null = staff template
```

**Replace `SubtaskCompletion` with `SubtaskEnrollment`:**

```python
class SubtaskEnrollment(models.Model):
    enrollment = models.ForeignKey(TaskEnrollment, related_name='subtask_enrollments')
    subtask = models.ForeignKey(Subtask, related_name='enrollments')
    status = models.CharField(choices=Task.Status.choices, default=TODO)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [UniqueConstraint(fields=['enrollment', 'subtask'])]
```

- On **task enroll** (or first open): create `SubtaskEnrollment` for each template subtask (`added_by is null`).
- **Participant subtask** (`added_by=student`): auto-create `SubtaskEnrollment` for that student’s enrollment only.

**Deprecate:** `SubtaskCompletion` — data migration: completed → `status=done`, not completed → `todo`.

**Progress % on enrollment:** derive from subtask enrollments (e.g. % with `status=done`) instead of boolean count; fallback to task `enrollment.status` when no subtasks.

### UI

| Surface | Change |
|---------|--------|
| `_subtasks_section.html` | Row = title + priority chip + due + **inline status buttons** (like task status, HTMX) — **no** milestone checkbox |
| Staff task form | Subtask lines: title + optional priority/due (description expand optional) |
| Student detail | Change own subtask status; optional edit participant subtask title only (v1) |
| Staff detail | Template subtasks list with metadata; per-student subtask status in enrollment table |

### Permissions

- `can_toggle_subtask` → rename **`can_change_subtask_status`**
- `can_edit_subtask_metadata` — staff on template subtasks; student on own `added_by` rows only

### Goals unchanged

**Milestones** stay checkbox + % toward goal completion — no status/priority on milestones. Docs should state: **Goals = outcomes with milestones; Tasks = work items with subtasks that track execution like mini-tasks.**

---

## Product decisions to confirm

| # | Question | Proposal |
|---|----------|----------|
| 1 | Group shared subtask status | **Per enrollment** (each student marks their copy) — aligns with cohort; group shared task status stays at task level |
| 2 | Staff edits template subtask fields after assign | Allowed; does not reset student `SubtaskEnrollment` status |
| 3 | Blocked status on subtasks | Include all four statuses (same as parent task) |
| 4 | Nested subtasks | **No** in v1 (flat list only) |

---

## Implementation phases

### Phase 1 — List status bug (ship first)

- [ ] `_task_status_inline.html` + update `_task_table.html`
- [ ] Adjust `task_quick_status` for list fragment response
- [ ] Tests: student list HTMX status change

### Phase 2 — Schema

- [ ] `Subtask` new fields
- [ ] `SubtaskEnrollment` model + migration from `SubtaskCompletion`
- [ ] Enrollment sync helper (create missing subtask enrollments)

### Phase 3 — UI & services

- [ ] Rewrite `_subtasks_section.html`
- [ ] `subtask_status` HTMX endpoint (replace `subtask_toggle`)
- [ ] Staff form subtask rows
- [ ] Update `progress` properties on `TaskEnrollment`

### Phase 4 — Docs & cleanup

- [ ] `info/topics/tasks.md`, `goals.md` comparison
- [ ] Remove dead `SubtaskCompletion` code paths
- [ ] Admin inlines

---

## Files to touch

| Bug | `templates/tasks/_task_table.html`, `_task_status_section.html`, `views.task_quick_status`, tests |
| Subtasks | `tasks/models.py`, `migrations/`, `services.py`, `permissions.py`, `views.py`, `urls.py`, `forms.py`, templates, `admin.py`, tests |

---

## Related docs

- [UI_LAYOUT_IMPROVEMENT_PLAN.md](UI_LAYOUT_IMPROVEMENT_PLAN.md) — create CTA on list card (tasks)
- [ENTITY_RESOURCE_CONTAINER_PLAN.md](ENTITY_RESOURCE_CONTAINER_PLAN.md) — materials link on task form (orthogonal)
