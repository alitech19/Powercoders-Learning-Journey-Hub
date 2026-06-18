## Goals list {#list}

Your goals and staff-assigned goal templates. Progress shows completed milestones vs total.

**Private** goals are only visible to you; **shared** goals let your teacher see progress.

## Goal detail {#detail}

Milestones checklist, status, and optional feedback from staff. Toggle milestones to update progress. Milestones are **on/off only** (no Doing/Blocked) — unlike **task subtasks**, which support full execution status. Linked **Materials** appear as **Open materials**; staff drafts with a schedule show **Scheduled publication**.

## Create goal {#form-create}

### Field order (staff create)

1. **Goal title** and **Description**
2. **Materials (Resources)** — optional
3. **Category**, **Status** (when shown), **Target date**
4. **Assign to students** — cohort/group and student checkboxes
5. **Milestones**
6. **Visibility** — toggle buttons at the bottom
7. **Scheduled publication** — when **Draft (staff only)** is selected
8. **Create goal**

### Goal title (required)

What you want to achieve — shown on cards and the detail page.

### Description

Optional context, links, or how you will know the goal is done.

### Materials (Resources)

Staff only on create/edit. Optional **Themes** board — **None**, link existing, or create new (`Materials: {goal title}` default). Enrolled students use **Open materials** on the goal detail page.

### Category

Organises the goal in your list:

- Hard Skill, Soft Skill, Language, Project, Career, Other — filter/grouping only, no permissions effect.

### Target date

Optional deadline for the whole goal (not per milestone).

### Status (when shown)

**Not started · In progress · Completed · Abandoned** — overall enrollment status; milestones can auto-update progress.

### Milestones

Add lines before save (e.g. “Finish module 3”, “Pass mock interview”). On the detail page you tick milestones; **milestones done / total** drives progress display. For step-by-step work with status and due dates, use **Tasks** and their subtasks instead.

### Assign to students (staff only)

1. Choose **Cohort** or **Group**.
2. Select the cohort/group radio target.
3. Expand and check students (or select all).

Creates **one goal template** with an **enrollment per student** — each student ticks milestones independently.

### Visibility

Toggle buttons at the bottom of the form:

**Students**

- **Only me** — private goal.
- **Share with teachers** — teachers see goal text and milestone progress.

**Staff**

- **Draft (staff only)** — hidden from students until you switch to **Share with students**.
- **Share with students** — each enrolled student sees the goal in their list.

### Scheduled publication

Shown only when **Draft (staff only)** is selected:

- **Publish automatically at…** with date/time (platform timezone).
- Assignment notifications go out when the goal becomes shared; manual **Share with students** cancels the schedule.
- Staff see the planned time on the goal detail page until it fires or is cancelled.

## Edit goal {#form-edit}

Change text, milestones, category, dates, **materials**, visibility, and **scheduled publication** where allowed. Removing milestones may confuse students who already completed them.

## Delete goal {#form-delete}

Removes goal and all enrollments.

## For students {#for-students}

Tick milestones as you go; status usually moves to In progress automatically.

## Admin notes {#admin-only}

<!-- role: admin -->

Admins can open shared goals; bulk fixes via Django admin if needed.
