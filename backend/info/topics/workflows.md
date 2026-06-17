## Workflows list {#list}

Shows workflows assigned to your cohort or group. **Shared** workflows have one progress bar for the group; **individual** workflows track each student separately.

## Workflow detail {#detail}

Steps checklist, enrollments (staff), progress, and optional **Open materials** link when staff attached a Resources theme. Staff see a **Scheduled publication** banner when a draft is set to go public automatically.

Complete steps in order when the workflow is configured that way.

## Create workflow {#form-create}

Staff only. One page when creating; **Save details** and **Assignment** are separate forms when editing.

### Field order (create)

1. **Title** and **Description**
2. **Materials (Resources)** — optional
3. **Assignment** — progress mode, cohort/group, students
4. **Steps** — at least one step on create (you can add more later on the detail page)
5. **Visibility** — toggle buttons at the bottom
6. **Scheduled publication** — appears when **Private** is selected
7. **Create workflow**

### Title (required)

Programme name shown in lists.

### Description

Instructions students read on the workflow page.

### Materials (Resources)

Optional **Themes** board linked to this workflow:

- **None** — no materials link on the detail page.
- **Link existing theme** — pick a thematic container from the picker (staff-created themes only).
- **Create new** — title defaults to `Materials: {workflow title}` (editable).

All enrolled students who can view the workflow see **Open materials** on the detail page.

### Assignment

**Progress mode**

- **Shared (cohort/group moves together)** — one completion state: when any authorised user completes a step for the group workflow, it applies to the shared progress (used for class-wide milestones).
- **Individual (per student)** — each enrolled student checks off steps on their own copy of progress.

**Target type**

- **Cohort** — assign at cohort level then pick students.
- **Group** — assign within one study group.

**Student selection** (individual mode)

After choosing cohort/group, check students to enroll. Only enrolled students see the workflow.

### Steps

Add one or more steps before saving (title, optional description, “requires previous step”). After creation you can still **Add step** on the workflow detail page; order is the order students follow.

### Visibility

Toggle at the bottom of the form (not a dropdown):

- **Private (staff only)** — draft hidden from students.
- **Public** — students in the assignment can see the workflow (after enrollment).

### Scheduled publication

Shown only when **Private** is selected:

- Check **Publish automatically at…** and pick date/time (platform timezone, e.g. Europe/Zurich).
- Students stay unaware until that time; assignment notifications are sent when the workflow becomes public.
- Switching to **Public** manually **cancels** the schedule.
- Staff see the planned time on the workflow detail page until it fires or is cancelled.

## Edit workflow {#form-edit}

**Save details** — title, description, materials, visibility, and scheduled publication (same rules as create).

**Assignment** section — change enrollments or modes where the UI allows (separate save).

## Delete workflow {#form-delete}

Deletes workflow, steps, and all completion data.

## For students {#for-students}

Open the workflow from the list; complete steps in order. Shared workflows mean the whole group shares one progress bar.

## Admin notes {#admin-only}

<!-- role: admin -->

Use Django admin if the UI cannot fix enrollment issues.
