# Entity Resource Container Links

## Goal

When creating or editing a **Workflow**, **Task**, or **Goal**, staff (and where relevant students) can attach an optional link to an existing **thematic** Resources container (Themes) or **create a new** theme inline. Assignees open materials from the entity detail page in one click.

Uses the **existing thematic container type** — no new container type, nothing cohort-specific in the data model. **All assignees** of the workflow/task/goal may view the linked theme, including cohort-wide assignments (students from different study groups).

**Documentation only** — no implementation in this pass.

---

## Product decisions (agreed)

| # | Decision |
|---|----------|
| 1 | **Assignees see materials** — anyone who can view the entity may open the linked container from detail |
| 2 | **Existing Themes (thematic) only** — no new container type; **no** cohort-specific container; **no** “materials group” dropdown. Staff picks or creates a **thematic** board; **all assignees** reach it via the entity link (not via belonging to one study group) |
| 3 | **Not group system tile** — picker excludes `is_system=True` group chat containers |
| 4 | **Workflow level only** — one container per workflow/task/goal; not per step |
| 5 | **Inline title** — default `Materials: {entity.title}`, **editable** before save |

| Rule | Detail |
|------|--------|
| **Optional** | Link never required |
| **Staff** | Create/edit on workflow, task, goal forms — link **thematic** or create new theme |
| **Students** | Personal task/goal → **Personal** container only |
| **One FK** | `resource_container` on Workflow, Task, Goal |
| **Reuse** | Same thematic theme may be linked from multiple entities |
| **Cohort workflow** | Same as group workflow: one thematic container; every enrolled student opens it from workflow detail — access via **entity**, not via sharing one group’s Themes tab membership alone |
| **Resources UI** | Linked containers live on existing **Themes** tab (no new Activity tab) |
| **Module off** | Hide picker; stub on open ([APP_MODULE_TOGGLES_PLAN.md](APP_MODULE_TOGGLES_PLAN.md)) |

---

## Product context

| Type | Entity linking |
|------|----------------|
| **Personal** | Student personal task/goal only |
| **Group (system)** | **Not** linkable — chat auto-sync |
| **Thematic (Themes)** | **Yes** — materials for workflows, tasks, goals |

Thematic containers today are often created per study group on the Themes tab. Entity-linked themes may still have an optional `group` for organisation, but **assignee access must not depend** on the student being in that group when they are assignees of the parent entity (essential for **cohort** workflows).

---

## Data model

### No new `ContainerType`

Keep `THEMATIC` only for staff-linked materials.

### Schema adjustment (thematic + cohort)

Allow **`group` nullable** on `ResourceContainer` when `container_type=THEMATIC` and `is_system=False`:

- Entity-bound theme created for a **cohort** workflow may have `group=NULL`.
- Entity-bound theme for a **group** assignment may set `group=assignee_group` for easier discovery on Themes tab — optional, not required for access.

**No** `cohort` FK on container.

### Entity FKs

```python
# Workflow, Task, Goal — each:
resource_container = models.ForeignKey(
    'resources.ResourceContainer',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='workflows',  # / 'tasks' / 'goals'
)
```

**Validation on link:**

| Rejected | Allowed |
|----------|---------|
| `is_system=True` | `THEMATIC` for staff |
| `PERSONAL` / `GROUP` type on staff forms | `PERSONAL` for student own task/goal |

---

## Access control (critical)

### View thematic container

Extend `can_view_container(user, container)`:

1. **Existing rules** — personal owner; thematic/group tied to a group the user can access (unchanged for standalone themes).

2. **Entity assignee rule (new)** — if container is linked from any Workflow / Task / Goal that `can_view_*` grants for this user → **allow view** (and read items), even when `container.group` is null or is a different group than the student’s.

This gives **all cohort assignees** access without a separate cohort container type.

### Edit items

Unchanged baseline: staff who could edit thematic before, plus staff who `created_by` the container or can manage the linked entity.

Students: **view** staff-linked thematic on assigned entities; edit only personal containers on own entities.

---

## UX — create / edit forms

Partial: `includes/_resource_container_picker.html`  
**Materials (Resources)** — “Optional theme (link list). Assignees open it from this page.”

| Mode | UI |
|------|-----|
| **None** | Default |
| **Existing** | `<select>` of **thematic** containers the user may use (created by self, themes in accessible groups, or themes already linked to their entities) |
| **Create new** | Title — prefilled `Materials: {{ entity.title }}`, editable → creates `THEMATIC`, `is_system=False`, `group` optional (null OK for cohort) |

**No** `materials_group_id` field.

### Cohort workflow

Teacher assigns cohort → creates or selects thematic → adds links on theme detail → each enrolled student sees **Open materials** on workflow.

### Edit

Change, clear, or swap linked thematic on entity edit.

---

## UX — detail pages

```text
Materials: [theme title]   →   Open materials
```

→ `resources:container_detail` for linked thematic.

Shown when `resource_container_id` set and viewer passes `can_view_container` (including entity assignee rule).

Below description; above steps / subtasks / milestones.

---

## Services (design)

`resources/services.py`:

```python
def resolve_resource_container_for_entity(
    *,
    user,
    mode: str,
    container_id: str | None,
    new_title: str | None,
    default_title: str,
    assignee_group: Group | None,  # optional — set group on new thematic when group-scoped assignment
) -> ResourceContainer | None:
```

`create` → `ResourceContainer(container_type=THEMATIC, title=…, group=assignee_group or None, created_by=user, is_system=False)`

Wire into workflow / task / goal create & update services.

---

## Resources index

No new tab. Entity-linked themes appear on **Themes** tab (with optional badge “Linked to workflow …” in polish phase). Filter/group chips behave as today; assignees primarily use entity detail link.

---

## Implementation phases

### Phase 0

- [ ] Entity FKs + nullable `group` on thematic (migration if needed)
- [ ] `can_view_container` entity-assignee rule
- [ ] `resolve_resource_container_for_entity()`

### Phase 1

- [ ] Staff forms + detail **Open materials**
- [ ] Picker: thematic only, no system group tile

### Phase 2

- [ ] Student personal → Personal only
- [ ] Cohort enrollment → all students open linked theme

### Phase 3

- [ ] Help topics; module toggle

---

## Success criteria

- [ ] Cohort workflow + **new** thematic `Materials: …` (edited title) → all enrolled students open materials from workflow
- [ ] Group workflow links to existing theme on Themes tab
- [ ] Student on assigned task sees thematic linked by teacher
- [ ] System group chat container **not** in picker
- [ ] No new container type in DB

---

## Related docs

- [APP_MODULE_TOGGLES_PLAN.md](APP_MODULE_TOGGLES_PLAN.md)
- [GROUP_SPACE_PROJECT_PLAN.md](GROUP_SPACE_PROJECT_PLAN.md)
- [frontend/ICON_SET.md](../../frontend/ICON_SET.md)
