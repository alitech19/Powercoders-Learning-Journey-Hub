# App Module Toggles (Admin Enable / Disable)

## Goal

Let **admins** turn integrated learning apps on or off at runtime (per PowerHUB instance), without redeploying.

When a module is **off**, users must not see it in **nav**, **dashboard**, or **chat entry points** (share tabs for off apps). Visiting the app’s URLs shows a **human-friendly stub page** (not a bare 404). Chat history and old snapshot posts stay **unchanged**. Data is not deleted.

**Not in scope:** per-cohort toggles; removing apps from `INSTALLED_APPS`; teacher/staff access to Django admin.

---

## Product decisions (agreed)

| Rule | Detail |
|------|--------|
| Who configures | **`Role.ADMIN` / superuser only** — in **Django admin** (`IntegratedModule` list). Teachers and other staff **cannot** open Django admin for toggles |
| Where toggles live | **Only Django admin** — no separate PowerHUB settings page in v1 |
| Scope | Org-wide, one flag per app |
| Default | All toggleable modules **enabled** after migration |
| Data | Disabled = hidden + stub URLs, not deleted |
| Core always on | `accounts`, `dashboard`, `info`, auth |
| Toggleable | `workflows`, `tasks`, `goals`, `reflections`, `journal`, `habits`, `group_space`, `resources`, **`bug_reports`** |
| **Release** | **One release:** visibility (nav, dashboard, chat) + middleware/stub pages together |

### Chat

| Topic | Decision |
|-------|----------|
| **Old messages** | Leave as-is — existing snapshots and text stay in the timeline |
| **Files / links in chat** | Always allowed in chat while **Чат** is on |
| **`resources` off** | Post still saved in chat; **no** sync to Resources app (same idea as “file not stored in disabled app”) |
| **Links in message body** | Same as files — visible in chat; no persistence under disabled **Resources**; links to other apps (e.g. `/tasks/5/`) **allowed** in the message |
| **Share panel tabs** | Hide kinds for disabled modules (no new snapshots from Goals app when goals off) |
| **Link to task detail** | Allowed in chat; if **Tasks** off, following link opens **stub**, not 404 |

### URLs & stubs

| Topic | Decision |
|-------|----------|
| Disabled app prefix | Render **`module_disabled.html`** stub (friendly copy), **not** default 404 |
| **Admin** on stub (PowerHUB UI) | Same stub as everyone, plus **extra line**: module can be re-enabled in **Django admin → Integrated modules** |
| **Teachers / students** | Stub without admin hint |
| Wrong id / real 404 | Separate friendly **`404.html`** (and other error pages) for unforeseen cases |

---

## Toggleable modules

| Slug | App | URL prefix | Nav group (UI plan) |
|------|-----|------------|---------------------|
| `workflows` | workflows | `/workflows/` | Learning |
| `tasks` | tasks | `/tasks/` | Learning |
| `goals` | goals | `/goals/` | Learning |
| `habits` | habits | `/habits/` | Learning |
| `reflections` | reflections | `/reflections/` | Wellbeing |
| `journal` | journal | `/journal/` | Wellbeing |
| `group_space` | group_space | `/group/` | Чат |
| `resources` | resources | `/resources/` | Resources |
| `bug_reports` | bug_reports | `/bugs/` | (no main nav — global bug button) |

---

## Visibility contract

When module `X` is **disabled**:

| Surface | Behaviour |
|---------|-----------|
| **Nav** | No item; empty nav group if all children off |
| **Dashboard** | No tiles, stats, or links to `X` |
| **Чат** | No share-tab for `X`; no new snapshot shares from `X`; old posts unchanged |
| **Oversight** | No columns for `X` |
| **Other templates** | No buttons into `X` |
| **Direct URL** | Stub page for `/…/` prefix of `X` |
| **Django admin** | Only **admin role** users; `IntegratedModule` toggles + optional model admins for data repair (teachers denied) |

---

## Behaviour detail

### Chat (`group_space`)

- **`group_space` off** → no nav/dashboard chat; `/group/…` → **module stub** (Чат disabled).
- **`group_space` on**, **`resources` off**:
  - Composer: files/links OK; **skip** `sync_from_group_post` / Resources container.
  - Optional UX: drop “name for Resources” requirement when resources disabled (label optional).
- **`group_space` on**, **`tasks` off** (example):
  - Share panel: no “Task” tab for new snapshots.
  - Message may still contain `/tasks/123/` link → opens **task module stub** when clicked.
- **`share_create`**: reject `kind` for disabled module (no new snapshot); plain message + URLs unchanged.

Implementation: `build_share_menu()`, filtered `SHARE_KIND_PANEL`, `get_shareable_object()` checks `is_enabled`, `after_post_saved` skips resources sync when `resources` off.

### Stub page (`module_disabled`)

Template: `templates/errors/module_disabled.html` (extends `base.html`).

Content:

- Title: e.g. “Tasks are not available”
- Short explanation for end users (1–2 sentences, calm tone)
- Primary CTA: “Back to dashboard”
- **If `user.role == ADMIN`:** extra block with link to Django admin changelist for `IntegratedModule` and module name to enable

Middleware: `ModuleGateMiddleware` → `module_disabled_view(request, slug)` with HTTP **200** (page explains state; optional `X-Robots-Tag: noindex`).

Register named route for tests: `config:module_disabled`.

### Friendly error pages (unforeseen cases)

Replace/default Django error handlers with branded templates:

| Handler | Template | When |
|---------|----------|------|
| `handler404` | `errors/404.html` | Unknown URL, deleted object |
| `handler403` | `errors/403.html` | Permission denied |
| `handler500` | `errors/500.html` | Server error |
| (module off) | `errors/module_disabled.html` | Middleware gate |

Shared partial: `errors/_error_layout.html` — logo, message, dashboard link, support hint.

Configure in `config/urls.py` (DEBUG=False) and document that `DEBUG=True` still shows technical 500 for devs.

### Link detection in chat (optional enhancement)

If message body contains internal URLs to a **disabled** module, still store and display as today; no auto-strip. Click → stub. (No server-side rewrite of pasted URLs on save.)

Future: snapshot cards could add “Open task” link → stub when module off; v1 snapshots remain inline HTML only.

---

## Architecture

```text
config/
  models.py           IntegratedModule
  modules.py          MODULE_REGISTRY
  module_access.py    is_enabled(), enabled_slugs()
  middleware.py       ModuleGateMiddleware
  admin.py            IntegratedModuleAdmin (admin-only permissions)
  views.py            module_disabled_view
```

### `IntegratedModule` model

```python
class IntegratedModule(models.Model):
    slug = models.SlugField(unique=True)
    label = models.CharField(max_length=64)
    is_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
```

- Data migration: one row per registry slug, all enabled.
- Cache `is_enabled(slug)` ~60s; invalidate on `post_save`.

### `ModuleGateMiddleware`

1. Match path prefix → slug.
2. If toggleable and not `is_enabled` → return stub view (not `Http404`).
3. Skip: `/admin/`, `/accounts/`, `/health/`, static, login, `dashboard/`, `info/`.

### Django admin permissions

- Register `IntegratedModule` with `list_editable = ('is_enabled',)`.
- `has_module_permission` / `has_change_permission`: **only** `request.user.role == ADMIN` or `is_superuser`.
- **Teachers:** no access to Django admin (enforce existing policy or tighten `ModelAdmin` if teachers had partial access).
- Toggling updates `updated_by` on save.

### Navigation & context

- `integrated_nav_items()` filters by `is_enabled`.
- Context processor `enabled_modules` for templates.
- Dashboard / oversight filter by slug set.

---

## Dependencies

| If disabled | Effect |
|-------------|--------|
| `resources` | No Resources sync from chat; Resources URLs → stub |
| `group_space` | No chat; no share UI |
| `tasks` / `goals` / … | No nav; share tab hidden; detail URLs → stub; chat links to those URLs → stub |

No auto-cascade disable in v1; document combos in `IntegratedModule` admin help text.

---

## Implementation phases (single release)

### Phase A — Core

- [ ] Model + migration + registry + cache
- [ ] Django admin (admin-only)
- [ ] `module_disabled` view + template (+ admin hint block)
- [ ] `ModuleGateMiddleware`
- [ ] Friendly `404` / `403` / `500` handlers + templates

### Phase B — Visibility

- [ ] Nav filter
- [ ] Dashboard + oversight
- [ ] Chat: share panel, `build_share_menu`, `share_create` guard, resources sync skip

### Phase C — Tests & docs

- [ ] Tests: stub not 404, admin hint, chat sync off, nav filter
- [ ] Admin help topic / `info` for admins
- [ ] [USABILITY_TESTING.md](../USABILITY_TESTING.md) scenarios

---

## Files to touch

| Area | Files |
|------|--------|
| Model / admin | `config/models.py`, `config/admin.py`, migration |
| Gate | `config/middleware.py`, `config/views.py`, `settings.MIDDLEWARE` |
| Errors | `templates/errors/*.html`, `config/urls.py` handlers |
| Nav / CP | `config/nav.py`, `config/context_processors.py` |
| Chat | `group_space/views.py`, `snapshots.py`, `services.py`, composer templates |
| Dashboard | `dashboard/views.py`, `dashboard.html` |
| Oversight | `accounts/student_oversight.py`, metric templates |
| Tests | `config/tests/test_modules.py`, middleware, nav, group_space sync |
| Docs | [TODO.md](TODO.md) |

---

## Success criteria

- [ ] Admin disables **Tasks** in Django admin → no Tasks in nav/dashboard/share tab; `/tasks/…` → **stub**; admin sees enable hint on stub
- [ ] Student opens `/tasks/5/` from chat link while Tasks off → **stub**, not Django 404
- [ ] **Resources** off: file/link post in chat remains; no `ResourceItem` created
- [ ] Old goal snapshot in chat still visible when Goals off
- [ ] Teacher cannot change `IntegratedModule` in admin
- [ ] Unknown URL shows friendly **404** page
- [ ] One release ships A + B + C

---

## Related docs

- [UI_LAYOUT_IMPROVEMENT_PLAN.md](UI_LAYOUT_IMPROVEMENT_PLAN.md) — nav groups
- [GROUP_SPACE_PROJECT_PLAN.md](GROUP_SPACE_PROJECT_PLAN.md) — Чат label
- [SCHEDULING_AND_REMINDERS_PLAN.md](SCHEDULING_AND_REMINDERS_PLAN.md) — skip jobs when module off (follow-up)
