Your home screen at `/` is **role-based**: students see learning shortcuts; teachers see oversight for their groups; admins see system metrics and staff tools.

## Student dashboard {#overview}

Summarises your learning activity and links into each app (same order as the top navigation).

| Area | What you see |
|------|----------------|
| **Workflows** | Featured card — enrolled and in-progress programmes. |
| **Goals · Tasks · Reflections** | Three cards with counts; open the full app from each card. |
| **Journal · Habits · Group · Resources** | Activity stats; Journal may show your latest entries. |

- A **weekly reflection due** banner appears when you have not submitted this week’s check-in.
- **Tasks** on the dashboard are a summary only — open **Tasks** in the nav for Individual, Group, and Cohort lists and to create work.
- You do **not** manage cohort or group membership here; staff assign that.

## Teacher dashboard {#overview-teacher}

Focuses on **students in groups you teach**, aligned with nav order (Workflows → Goals → Tasks → Reflections → Journal → Habits → Group → Resources).

| Area | What you see |
|------|----------------|
| **Quick links** | Jump to Workflows, Goals, Assign task, Reflections, Group chat, Resources. |
| **Missing reflection** | Chips for students without a weekly reflection this week; **View all** opens Student Progress filtered. |
| **Summary tiles** | Student count, your groups, group posts (7d), link to group chat. |
| **Student overview** | Preview table (metrics per student); **Full progress** opens the full list. |
| **Your Groups** | Cards per group with a link to **group chat** (not a task inbox on the dashboard). |

- Open **Student Progress** (`/accounts/students/progress/`) for search, filters, and cohort/group columns.
- **Student detail** shows tabs across workflows, goals, tasks, reflections, journal, and habits (shared views where policy allows).
- You **do not** see students’ private personal tasks on the dashboard — use Tasks or student detail for assigned/shared work.
- **Assign task** in quick links creates group/cohort tasks; day-to-day teaching paths often start from **Workflows** or **Goals**.

## Admin dashboard {#overview-admin}

<!-- role: admin -->

System-wide **read-only metrics** plus in-app **Management** (staff UI — not only Django admin).

### Metric tiles

| Tile | Meaning |
|------|---------|
| Students / Teachers | Counts; Students and Teachers tiles link into user management filters. |
| Active cohorts / Groups | Cohort and group structure; cohort tile links to **Cohorts & Groups**. |
| Journal entries (7d) | Platform-wide journal activity. |
| Active habits / Workflows / Group posts (7d) / Resource links | Engagement and content volume. |

### Management block

| Action | Purpose |
|--------|---------|
| **Cohorts & Groups** | Create cohorts and groups, assign teachers, bulk-assign students (US-39). |
| **Student Progress** | Cross-app metrics per student; drill down to student detail. |
| **Users** | List, filter by role, create, deactivate/reactivate, admin delete. |
| **+ Create user** / **↑ Import users (CSV)** | Onboarding; import follows the CSV template on the import page. |
| **Audit log (admin)** | Django admin changelist for `AuditLog` (middleware records sensitive actions). |

Django admin remains available for edge cases (raw model edits, rare fields). Prefer the **Management** cards for day-to-day operations.

### What is not on the admin dashboard

- No global **task tables** on the home page — tasks are managed per app or via student detail.

## Operations note {#planned-platform}

<!-- role: admin -->

| Item | Where |
|------|--------|
| GDPR export / self-delete | **Profile** → Your data (Markdown export, delete account) |
| Notification centre | Nav bell → `/accounts/notifications/` |
| Welcome email + Slack on user create/import | Automatic when `EMAIL_*` and optional `SLACK_WEBHOOK_URL` are set |
| Weekly missing-reflection Slack | Celery `accounts.tasks.notify_missing_reflections` — register in Beat ([TODO.md](../../../docs/TODO.md)) |

## For students {#for-students}

Teachers and admins can read student-oriented sections in other ⓘ help pages to see what participants experience on each screen.
