## Workflows list {#list}

Shows workflows assigned to your cohort or group. **Shared** workflows have one progress bar for the group; **individual** workflows track each student separately.

## Workflow detail {#detail}

Steps checklist, enrollments (staff), and progress. Complete steps in order when the workflow is configured that way.

## Create workflow {#form-create}

Staff only. Two parts on one page (when creating) or split when editing.

### Details

**Title (required)** — programme name shown in lists.

**Description** — instructions students read on the workflow page.

**Visibility**

- **Public** — students in the assignment can see the workflow (after enrollment).
- **Private** — draft hidden from students until you set Public.

### Assignment

**Progress mode**

- **Shared (cohort/group moves together)** — one completion state: when any authorised user completes a step for the group workflow, it applies to the shared progress (used for class-wide milestones).
- **Individual (per student)** — each enrolled student checks off steps on their own copy of progress.

**Target type**

- **Cohort** — assign at cohort level then pick students.
- **Group** — assign within one study group.

**Student selection** (individual mode)

After choosing cohort/group, check students to enroll. Only enrolled students see the workflow.

Steps are added **after** creation on the workflow detail page (Add step). Order on that page is the order students follow.

## Edit workflow {#form-edit}

**Save details** — title, description, visibility only.

**Assignment** section — change enrollments or modes where the UI allows.

## Delete workflow {#form-delete}

Deletes workflow, steps, and all completion data.

## For students {#for-students}

Open the workflow from the list; complete steps in order. Shared workflows mean the whole group shares one progress bar.

## Admin notes {#admin-only}

<!-- role: admin -->

Use Django admin if the UI cannot fix enrollment issues.
