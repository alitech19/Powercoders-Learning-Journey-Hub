# Bug Bounty / Bug Reports App

## Goal

Add a toggleable Django app **`bug_reports`** so users can report issues from any page via a **crosshair (bug)** button next to the **ⓘ help** control. Reports are stored in the database; **admins** triage on a dedicated inbox, reply in-app, and trigger email notifications. Other admins see who is handling a report to avoid duplicate work.

Integrates with [APP_MODULE_TOGGLES_PLAN.md](APP_MODULE_TOGGLES_PLAN.md) — slug `bug_reports`, default **enabled** (or **disabled** per org preference on migration).

---

## Product decisions (agreed)

| Rule | Detail |
|------|--------|
| **Separate app** | `bug_reports` — own models, urls, templates, admin |
| **Toggle** | Admin enables/disables via `IntegratedModule` (`bug_reports`); when off: no bug button, `/bugs/` → module stub |
| **Who can report** | Any **authenticated** user (student, teacher, admin) |
| **Bug button placement** | Next to **ⓘ** after page title (inline header row) — crosshair / sniper-scope icon |
| **Report form** | Auto-filled **page URL** (absolute, from referring page); user enters **description**; **Submit** |
| **Storage** | PostgreSQL — reports + admin replies |
| **Admin inbox** | PowerHUB page (list + detail), plus **Django admin** (reporter email visible) |
| **Email on submit** | Reporter: “received, under review”; **All admins**: “new bug report” |
| **Admin reply** | Text reply on detail → email to reporter |
| **Workflow** | Admin: **take in progress**, **close**, **reject**, **reopen** — status + assignee visible to all admins on list |

---

## UX

### Global bug button (when module enabled)

```text
[ Page title ]  [ⓘ]  [🎯 crosshair]
Short purpose subtitle…
```

- Shown in `_page_header.html` (or context on all pages with `page_help`).
- Link: `{% url 'bug_reports:create' %}?from={{ request.get_full_path|urlencode }}`
- `aria-label`: “Report a bug on this page”
- Hidden if: not authenticated, module `bug_reports` disabled.

Icon: volumetric tile style per [frontend/ICON_SET.md](../../frontend/ICON_SET.md).

### Create report page

| Field | Source |
|-------|--------|
| **Page URL** | Read-only, prefilled from `?from=` (validated same-origin path or full `SITE_URL` + path); fallback `request.META.get('HTTP_REFERER')` |
| **Description** | Required textarea |
| Submit | POST → save → thank-you / redirect with flash |

Optional: category dropdown (UI bug / data / other) — **v2**.

### Reporter confirmation

After submit: message “Thanks — we’ll review your report.” In-app notification optional v2.

### Admin — report inbox (`/bugs/inbox/`)

**Admin role only** (and superuser).

**List columns:** ID, status, page URL (truncated), reporter name + email, assigned admin, created, updated.

**Filters:** status, assigned to me, unassigned, open.

**Row badges:**

| Status | Meaning |
|--------|---------|
| `submitted` | New |
| `in_progress` | Someone took it (`assigned_to` set) |
| `closed` | Resolved |
| `rejected` | Won’t fix / invalid |
| `reopened` | Was closed/rejected, active again |

**Visibility rule:** When status is `in_progress`, show **“Handled by: {admin display_name}”** so a second admin does not duplicate triage.

### Admin — report detail

- Full URL, description, reporter (name, email, role, group)
- **Actions** (POST, permission-checked):
  - **Take in progress** — sets `assigned_to=request.user`, status `in_progress` (fails if already taken by another admin unless superuser reassign — v1: block double-take)
  - **Close** / **Reject** / **Reopen** — with optional internal note (v1 note optional)
- **Reply** form — creates `BugReportMessage` (author=admin, `is_staff_reply=True`) → triggers email to reporter
- Thread: chronologic messages (admin replies; v2 user follow-up)

### Django admin

Register `BugReport`, `BugReportMessage` — list_display: id, status, reporter email, assigned_to, created_at; inline replies.

---

## Data model

### `BugReport`

| Field | Type | Notes |
|-------|------|-------|
| `reporter` | FK `User` | Who submitted |
| `page_url` | CharField(2048) | Full URL at submit time |
| `page_path` | CharField(512) | Path + query for filtering (denormalized) |
| `description` | TextField | User text |
| `status` | CharField choices | See workflow |
| `assigned_to` | FK `User`, null | Admin handling |
| `assigned_at` | DateTime, null | When taken |
| `closed_at` | DateTime, null | |
| `created_at` / `updated_at` | DateTime | |

```python
class Status(models.TextChoices):
    SUBMITTED = 'submitted', 'Submitted'
    IN_PROGRESS = 'in_progress', 'In progress'
    CLOSED = 'closed', 'Closed'
    REJECTED = 'rejected', 'Rejected'
    REOPENED = 'reopened', 'Reopened'
```

Indexes: `(status, created_at)`, `(assigned_to, status)`.

### `BugReportMessage`

| Field | Type |
|-------|------|
| `report` | FK `BugReport` |
| `author` | FK `User` |
| `body` | TextField |
| `is_staff_reply` | BooleanField |
| `created_at` | DateTime |

---

## Permissions

| Action | Who |
|--------|-----|
| Submit report | Authenticated + module enabled |
| View inbox / detail | `Role.ADMIN` / superuser |
| Take / close / reject / reopen | Admin |
| Reply | Admin (prefer `assigned_to` or any admin v1 — document: any admin can reply; **take** prevents duplicate work) |

---

## Email notifications

New module `bug_reports/emails.py` (or extend `accounts.emails`):

| Event | Recipients | Subject (example) |
|-------|------------|-------------------|
| Report created | Reporter | “We received your bug report” |
| Report created | All active admins (`role=ADMIN`, `is_active`) | “New bug report #{id}” |
| Admin reply | Reporter | “Update on your bug report #{id}” |

Use `SITE_URL` + link to report detail for admins (admin-only URL).

Respect future per-user email toggles if present; v1 admins always get new-report email.

Celery optional v2 — v1 synchronous `send_mail` in try/except like `accounts.emails`.

---

## Module toggle integration

Add to `MODULE_REGISTRY` in [APP_MODULE_TOGGLES_PLAN.md](APP_MODULE_TOGGLES_PLAN.md):

| Slug | App | URL prefix |
|------|-----|------------|
| `bug_reports` | bug_reports | `/bugs/` |

When disabled:

- Context `bug_report_enabled=False` → no crosshair button
- `ModuleGateMiddleware` → stub for `/bugs/`
- Inbox not linked from nav (admin uses direct URL or Django admin only when enabled)

**Not** in main Learning nav groups — optional link under admin dashboard when enabled.

---

## URLs (`bug_reports/urls.py`, `app_name = 'bug_reports'`)

| Path | View | Who |
|------|------|-----|
| `new/` | `report_create` | Authenticated |
| `submit/` | POST `report_submit` | Authenticated |
| `inbox/` | `report_list` | Admin |
| `inbox/<pk>/` | `report_detail` | Admin |
| `inbox/<pk>/take/` | POST | Admin |
| `inbox/<pk>/close/` | POST | Admin |
| `inbox/<pk>/reject/` | POST | Admin |
| `inbox/<pk>/reopen/` | POST | Admin |
| `inbox/<pk>/reply/` | POST | Admin |

Mount: `path('bugs/', include('bug_reports.urls'))` in `config/urls.py`.

---

## Context processors

```python
def bug_report_button(request):
    return {
        'bug_report_button': BugReportButton(
            enabled=is_module_enabled('bug_reports') and request.user.is_authenticated,
            create_url=... with from=full_path,
        ),
    }
```

Register in `settings.py` next to `page_help`.

---

## Workflow rules (concurrency)

| Action | Rule |
|--------|------|
| **Take in progress** | Only if `status in (submitted, reopened)` and (`assigned_to is null` OR assigned_to=self) |
| **Take by B when A has it** | Show error “Already handled by A” — no overwrite in v1 |
| **Close / reject** | Admin; sets status, `closed_at` |
| **Reopen** | From `closed` or `rejected` → `reopened`, clear `assigned_to` optional or keep history |

---

## Implementation phases

### Phase 0 — App skeleton

- [ ] `bug_reports` app, models, migrations
- [ ] `IntegratedModule` row `bug_reports`
- [ ] Mount urls, module middleware slug

### Phase 1 — Submit flow

- [ ] Create form + emails on submit
- [ ] Bug button in page header + context processor
- [ ] Tests: submit, URL capture, permission

### Phase 2 — Admin inbox

- [ ] List + detail + status actions
- [ ] Take / close / reject / reopen
- [ ] Reply + email to reporter
- [ ] Django admin

### Phase 3 — Polish

- [ ] Dashboard tile for admins “Open bug reports (n)”
- [ ] Help topic `info/topics/bug_reports.md`
- [ ] Usability scenarios

---

## Files to touch

| Area | Files |
|------|--------|
| New app | `backend/bug_reports/` (models, views, urls, forms, emails, permissions, admin, tests) |
| Config | `settings.INSTALLED_APPS`, `urls.py`, `context_processors`, `modules.py` registry |
| Templates | `bug_reports/*.html`, `includes/_page_header.html`, optional `base.html` |
| Docs | `APP_MODULE_TOGGLES_PLAN.md` (add slug), `TODO.md` |

---

## Success criteria

- [ ] User on `/tasks/` clicks crosshair → form shows URL `/tasks/…` → submit → row in DB
- [ ] Reporter and all admins receive emails
- [ ] Admin A takes report → Admin B sees “In progress — A” on list
- [ ] Admin replies → reporter email with body
- [ ] Admin closes report; can reopen later
- [ ] Module `bug_reports` off → no button, `/bugs/new/` stub

---

## Related docs

- [APP_MODULE_TOGGLES_PLAN.md](APP_MODULE_TOGGLES_PLAN.md)
- [frontend/ICON_SET.md](../../frontend/ICON_SET.md) — volumetric icons + header row pattern
- [TASKS_STATUS_AND_SUBTASKS_PLAN.md](TASKS_STATUS_AND_SUBTASKS_PLAN.md)
