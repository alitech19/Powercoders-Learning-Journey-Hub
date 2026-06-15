## Administration menu {#overview}

<!-- role: admin -->

The **Administration** menu (top right, admins only) links to in-app staff tools. Prefer these pages over Django admin for day-to-day work.

| Tab | Purpose |
|-----|---------|
| Cohorts & Groups | Structure cohorts, groups, teacher assignment, student placement |
| Student Progress | Cross-app metrics per student |
| File storage | Google Drive configuration |
| Users | Search, filter, deactivate, delete |
| Create User / Import CSV | Onboarding |
| Audit log / Django Admin | Advanced / compliance |

Teachers reach **Student Progress** from the dashboard; other tabs are admin-only in the nav.

## Cohorts & Groups {#cohorts-groups}

<!-- role: admin -->

Manage the academic structure students belong to.

### Cohorts

- **New cohort** — name, status (planned / active / completed), start and end dates.
- Each cohort holds one or more **groups** (e.g. “Group A”, “Group B”).
- **Edit** / **Delete** from the cohort card. Deleting a cohort removes its groups (use with care).

### Groups

- **Add group** under a cohort — name and assigned **teachers** (who can see students in that group).
- **Assign students** — checkbox list of students in the cohort; a student can be in **one group** at a time. Moving them updates their `User.group` (affects Group chat, tasks, goals scoped to that group).
- **Edit** teachers on a group; **Delete** removes the group.

### Tips

- Create cohort + groups **before** bulk CSV import if you use `cohort` / `group` columns.
- Group names should be unique enough within a cohort when importing.

## Student Progress {#student-progress}

Overview table of students you are allowed to see:

| Who | Scope |
|-----|--------|
| **Admin** | All students |
| **Teacher** | Students in groups you teach |

### Columns

Metrics follow main nav order: **Workflows → Tasks → Goals → Habits → Reflections → Journal → Group Space → Resources** (counts or status per app).

### Filters

- **Group chips** — limit to one study group.
- **Missing reflection this week** — students without a weekly reflection in the current week.

Click a row → **Student detail** for tabs across workflows, goals, tasks, reflections, journal, and habits (shared / policy-visible data only).

## Student detail {#student-detail}

Drill-down for one student: enrollments and activity per app. Use this for 1:1 check-ins — not for editing their private journal text.

- **Back** returns to Student Progress with your filters.
- Teachers only see students in assigned groups.

## Users {#users}

Search by name or email; filter by role (admin / teacher / student). Paginated list (25 per page).

| Who | What you see |
|-----|----------------|
| **Admin** | All users; role filters; deactivate, reactivate, delete |
| **Teacher** | Students in your groups only (read-only list) |

### Admin actions

<!-- role: admin -->

| Action | Notes |
|--------|--------|
| **Deactivate** | Blocks login; data retained |
| **Reactivate** | Restores access |
| **Delete account** | Permanent erasure (GDPR-style); confirm carefully |

## Create User {#create-user}

Single-account onboarding:

1. Email, display name, role, optional cohort/group.
2. System generates a **temporary password** (shown once).
3. User must change password on first login.
4. Welcome email sends when mail is configured; optional Slack ping for staff.

Copy the temporary password immediately — it is not shown again.

## Import Users (CSV) {#import-users}

<!-- role: admin -->

Bulk create from a CSV file.

**Required columns:** `email`, `display_name`

**Optional:** `role` (`student` / `teacher` / `admin`), `cohort`, `group` (matched by name, case-insensitive)

After upload you get a summary: **Created** (with temp passwords), **Skipped** (duplicate email), **Errors** (missing fields). Welcome email + Slack run per created user when configured.

Example:

```
email,display_name,role,cohort,group
alice@example.com,Alice Smith,student,Cohort 2026,Group A
```

## Audit log {#audit-log}

<!-- role: admin -->

Django admin changelist for **Audit log** entries. Middleware records sensitive actions (e.g. admin paths, account changes). Read-only review for compliance — not for day-to-day editing.

## Django Admin {#django-admin}

<!-- role: admin -->

Full Django admin index: raw model access, periodic Celery Beat tasks, Google storage models, and edge-case fields.

Use **Administration** pages first; open Django admin when you need Beat schedules, upload logs, or direct model edits.

## File storage {#file-storage}

<!-- role: admin -->

**Administration → File storage** — Google Drive for group chat and Resources.

| Toggle | Who it affects |
|--------|----------------|
| **Enable staff uploads** | Teachers/admins → org **Shared drive** (Workspace Shared drive + GCP **service account JSON**) |
| **Enable student OAuth uploads** | Students → **My Drive** (GCP **OAuth client ID + secret**) |

These are **independent**. Full step-by-step in ⓘ help on File storage:

- Students (Gmail MVP): *Student OAuth — Google Cloud* / *PowerHUB*
- Organisation (Workspace): *Google Workspace*, *service account*, *PowerHUB staff*, *Students with Google Workspace*

Repo: `docs/GOOGLE_DRIVE_SETUP.md`.
