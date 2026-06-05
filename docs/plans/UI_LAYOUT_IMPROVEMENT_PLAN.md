# UI & Layout Improvement Plan

## Goal

Improve PowerHUB frontend consistency and reduce nav clutter based on teacher feedback: group related apps in navigation, unify icons, reposition help and create actions, add short “what is this tool for?” copy on every screen, and consolidate account controls into an avatar menu.

No backend domain changes — templates, `config/nav.py`, context processors, and optional small view context helpers.

---

## Product decisions (agreed)

| Area | Decision |
|------|----------|
| **Nav groups (4)** | 1) **Learning** (навчання) — Workflows, Tasks, Goals, **Habits** · 2) **Wellbeing** — Reflections, Journal · 3) **Чат** · 4) **Resources** |
| **Icons** | **One style app-wide — volumetric only**; see [App-wide icon system](#app-wide-icon-system) |
| **Help (ⓘ)** | Smaller; placed **immediately after the page title** (top-left row), not floating top-right of `<main>` |
| **Page purpose** | Every list/hub page shows a **short subtitle** (what the tool is for); separate from long help topic |
| **Create actions** | On the **entity list card** (e.g. tasks card), **top-right** — never in the global page header; see [Create button placement](#create-button-placement) |
| **Account** | **Avatar dropdown**: display name, Profile, Log out; remove separate Profile / name / Log out text from navbar |

---

## App-wide icon system

### Problem today

The UI mixes **flat outline SVG** (nav bell, student dashboard Goals/Tasks) and **volumetric** tiles (emoji in colored rounded boxes on admin dashboard). Product decision: **volumetric everywhere** — one component, one container style.

### Agreed style: **volumetric** (only)

**Volumetric** = glyph inside a **filled tile** (`rounded-lg` / `rounded-xl`, background color, `shadow-sm`) — reads as solid / “3D sticker”, not a thin outline on empty background.

| Must use volumetric | Remove from product chrome |
|---------------------|----------------------------|
| Nav (groups + dropdown items) | `stroke`-only Heroicons (e.g. dashboard Goals/Tasks rows) |
| Dashboard app tiles | Bare emoji without tile (`text-5xl` on gray background) |
| List empty states | Flat SVG icons |
| Notifications bell in navbar | Outline-only bell SVG |

**User-generated content** (e.g. journal mood emoji chosen by student) stays as-is — not part of the design system.

### Standard component: `_volumetric_icon.html`

One partial, same markup everywhere:

```django
{# size: sm | md | lg — maps to h-8/h-10/h-12 tile #}
<span class="volumetric-icon volumetric-icon--{{ size }} …">
  {% include icon_partial %}  {# or emoji char from ICON_MAP #}
</span>
```

**Visual rules (all volumetric icons):**

- Container: `rounded-lg` or `rounded-xl`, background `bg-[#C0392B]` or `bg-white/80` on cream cards, light `shadow-sm`
- Glyph: centered, consistent optical size (not raw `text-5xl` on the page)
- Same component in nav dropdown, dashboard, empty states, admin management cards

### Implementation path

| Phase | Approach |
|-------|----------|
| **2a (fast)** | Central `ICON_MAP` (concept → emoji) + `_volumetric_icon.html`; replace flat SVGs and naked emoji |
| **2b (optional polish)** | Replace emoji with a **single licensed 3D/duotone asset pack** (PNG or SVG with fill + shadow) — same partial API, swap glyph source |

**Concept map** (stable keys, one glyph per app):

| Key | App / group |
|-----|-------------|
| `workflows` | Workflows |
| `tasks` | Tasks |
| `goals` | Goals |
| `reflections` | Reflections |
| `journal` | Journal |
| `habits` | Habits |
| `chat` | Чат |
| `resources` | Resources |
| `learning` | Nav group Learning (parent) |
| `wellbeing` | Nav group Wellbeing (parent) |
| `notifications` | Bell (volumetric tile or filled bell glyph — not outline-only) |

Files: `frontend/templates/includes/_volumetric_icon.html`, `config/icon_map.py` (or `ICON_MAP` in `page_meta.py`).

### Migration checklist

- [x] `_volumetric_icon.html` + `ICON_MAP` + `{% volumetric_icon %}` tag — see [frontend/ICON_SET.md](../../frontend/ICON_SET.md)
- [x] `base.html` — notifications + nav dropdown children
- [x] Empty states: tasks, goals, habits, reflections, journal, workflows, group chat, cohorts
- [x] `dashboard/dashboard.html` — app tiles + management cards (layout unchanged; icons unified)
- [ ] Audit: remaining `stroke="currentColor"` in product chrome (welcome, forms, alerts — justify or convert)

Do **not** introduce new flat outline icons in future screens.

---

## Navigation redesign

### Current (`config/nav.py`)

Eight flat items: Workflows, Goals, Tasks, Reflections, Journal, Habits, Group, Resources.

### Target

Four top-level entries; first three open a **dropdown** (desktop) or **expandable section** (mobile):

```text
[ Logo ]  Learning ▾   Wellbeing ▾   Чат   Resources     [🔔]  [Адміністрування ▾]  [Avatar ▾]
```

**Admin only:** [ADMIN_RESTRUCTURE_PLAN.md](ADMIN_RESTRUCTURE_PLAN.md) — **Адміністрування ▾**: Django admin, **когорти/групи**, **масовий імпорт**, bug inbox. Users & student progress: **staff nav + dashboard** (shared with teachers).

| Nav label (UI) | Items | Default landing (click parent) |
|----------------|--------|--------------------------------|
| **Learning** | Workflows, Tasks, Goals, **Habits** | `workflows:list` |
| **Wellbeing** | Reflections, Journal | `reflections:list` |
| **Чат** | Single link | `group_space:feed` |
| **Resources** | Single link | `resources:index` |

**Rationale:** Habits = learning routines / discipline, grouped with assigned work; Reflections + Journal = wellbeing check-ins, separate from habits.

**Active state:** parent highlight if any child route is active (`url_name` prefix or explicit child list).

**Implementation:**

- Replace flat `NavItem` with `NavGroup` dataclass: `label`, `children: tuple[NavItem, ...]`, optional `default_url_name`.
- `integrated_nav_items()` → returns groups for template; keep backward-compatible helper for tests.
- Mobile: hamburger or collapse groups under labels (Alpine.js in `base.html`).

**Dashboard** stays off nav (logo → dashboard); update dashboard quick links to match four groups.

---

## Page header & help (ⓘ)

### Current

- `_page_header.html`: centered title, subtitle, centered CTA below.
- `_page_help_button.html`: `absolute top-4 right-5` on `<main>`; `main` has `pr-14` when help enabled.

### Target layout

```text
[ Title ] [ⓘ]                                    [ optional: no create here ]
Short purpose line (subtitle, max ~1–2 sentences)
─────────────────────────────────────────────────
┌─ List / content card ───────────────────────────── [ + New … ]  ← top-right
│  …
└──────────────────────────────────────────────────
```

### `_page_header.html` changes

- Row 1: `flex items-center gap-2` — `h1` + inline help link (smaller ⓘ: `h-6 w-6`, `text-xs`, not large circle).
- Row 2: `subtitle` = **purpose line** (required on hub/list pages).
- Remove `cta_url` / `cta_label` from page header (deprecated params — migrate to list card).

### `_page_help_button.html`

- Remove absolute positioning.
- Include from `_page_header.html` next to title.
- Drop `main.pr-14` from `base.html`.

### Purpose copy (single source)

Add `PAGE_PURPOSE` in `config/nav.py` or new `config/page_meta.py`:

```python
PAGE_PURPOSE = {
    'workflows:list': ('Workflows', 'Step-by-step learning paths your teachers assign.'),
    'tasks:task_list': (...),
    ...
}
```

Context processor `page_meta(request)` merges title override + purpose for current `view_name`. Templates use `page_meta.subtitle` when present, else fall back to per-view `subtitle` until migrated.

Long help (`info` topics) unchanged — opened via ⓘ only.

---

## Create button placement

### Rule (strict)

**Never** put “New Task”, “New Goal”, etc. in `_page_header.html` or under the page title.

| Page type | Create button location |
|-----------|------------------------|
| **List / index** | Top-right of the **card that lists entities** (tasks table card, goals list card, …) |
| **Empty state** | Same card — primary create top-right or centered inside empty card |
| **Detail / form** | Unchanged (Save / Cancel on form) |
| **Dashboard** | No global “create entity”; only deep links into apps |

### Example: Tasks (current vs target)

**Today** (`tasks/task_list.html`):

```django
{% include "_page_header.html" with title="My Tasks" cta_url=tasks_create_url cta_label="New Task" %}
… filters …
{% include "_task_table.html" %}  {# white card with tasks #}
```

**Target:**

```django
{% include "_page_header.html" with title="My Tasks" subtitle="…" %}  {# no cta_* #}
… filters …
<div class="bg-white rounded-xl border …">
  {% include "_list_card_header.html" with card_title="Tasks" create_url=tasks_create_url create_label="New Task" %}
  {% include "_task_table.html" %}
</div>
```

Same pattern for goals, workflows, habits (Learning), reflections/journal (Wellbeing), resources tabs.

### Template pattern

Partial: `includes/_list_card_header.html`

```django
<div class="flex items-center justify-between px-5 pt-5 pb-2 border-b border-gray-100">
  <h2 class="text-base font-semibold text-[#2B2B2B]">{{ card_title|default:" " }}</h2>
  {% if create_url %}
  <a href="{{ create_url }}" class="inline-flex …">+ {{ create_label }}</a>
  {% endif %}
</div>
```

Migrate:

- `workflows/list.html`, `goals/goal_list.html`, **`tasks/task_list.html`**, `reflections/list.html`, `journal/entry_list.html`, `habits/habit_list.html`, `resources/index.html`

Staff/student dual headers: one purpose line in page header only; **create** only on the list card when `can_create`.

---

## Avatar account menu

### Current (`base.html`)

Avatar + display name + Profile link + Log out form (inline).

### Target

- Click avatar → dropdown (Alpine `x-data="{ open: false }"`).
- Items:
  - **Header row:** `display_name` (non-clickable or links to profile)
  - **Profile**
  - **Notifications** (optional — moves bell into menu for cleaner bar; or keep bell — decide in Phase 2)
  - Divider
  - **Log out** (POST form button styled as menu item)
- Hide duplicate text links on `sm+` and mobile.
- Do **not** put Django admin in avatar menu — use **Адміністрування ▾** in navbar ([ADMIN_RESTRUCTURE_PLAN.md](ADMIN_RESTRUCTURE_PLAN.md)).

Accessibility: `aria-expanded`, keyboard escape, focus trap minimal.

---

## Scope by area

### Phase 1 — Foundation

- [x] `NavGroup` + dropdown nav in `base.html`
- [x] `page_meta` / `PAGE_PURPOSE` for all integrated apps
- [x] Refactor `_page_header` + inline ⓘ; remove `main.pr-14`
- [x] `_list_card_header` partial
- [x] Avatar dropdown (profile, logout, name)

### Phase 2 — List pages & volumetric icons

- [x] `_volumetric_icon.html` + `ICON_MAP` (4 sizes: xs/sm/md/lg); [frontend/ICON_SET.md](../../frontend/ICON_SET.md)
- [x] Move create CTAs into list cards (Learning + Wellbeing + Resources)
- [x] Nav + list empty states → volumetric component
- [x] Dashboard volumetric icons (tile layout may evolve in a separate dashboard plan)

### Phase 3 — Polish & mobile

- [x] Mobile nav for grouped items (hamburger sections)
- [ ] Update `info/topics/*.md` intros if purpose lines duplicate — keep help for depth
- [ ] Usability pass ([USABILITY_TESTING.md](../USABILITY_TESTING.md))

### Out of scope (this plan)

- **Dashboard layout redesign** (four-group layout restructure) — icons done here; layout may evolve separately
- Full design system / Figma
- Dark mode
- i18n (UI copy can stay EN in templates; nav label **Чат** is fixed Ukrainian per product decision)

---

## Files to touch (checklist)

| File | Change |
|------|--------|
| `backend/config/nav.py` | Nav groups, default routes, purposes |
| `backend/config/page_meta.py` (new) | Purpose strings |
| `backend/info/context_processors.py` | Optional merge with `page_help` |
| `frontend/templates/base.html` | Nav dropdown, avatar menu, drop `pr-14` |
| `frontend/templates/includes/_page_header.html` | Title + ⓘ + subtitle only |
| `frontend/templates/includes/_page_help_button.html` | Inline compact |
| `frontend/templates/includes/_list_card_header.html` (new) | Create top-right |
| `frontend/templates/includes/_volumetric_icon.html` (new) | Shared volumetric tile |
| `backend/config/icon_map.py` (new) | Concept → glyph |
| List templates per app | Card wrapper + create position |
| `frontend/templates/dashboard/dashboard.html` | Four-group layout, volumetric icons |
| [USABILITY_TESTING.md](../USABILITY_TESTING.md) | New nav tasks |

---

## Nav label reference (after grouping)

| Group | Children (order in dropdown) |
|-------|------------------------------|
| **Learning** | Workflows → Tasks → Goals → Habits |
| **Wellbeing** | Reflections → Journal |
| **Чат** | (feed) |
| **Resources** | (index) |

---

## Success criteria

- [x] Navbar shows **4** top-level items (not 8).
- [x] Teachers can reach any sub-app in ≤2 clicks from nav.
- [x] Every integrated list page has purpose subtitle + ⓘ beside title.
- [x] No create button in page header on list pages (e.g. **New Task** only on tasks list card, top-right).
- [x] Navbar right side: notifications (if kept) + avatar only — no loose Profile/Log out text.
- [x] All product chrome icons use the **volumetric** component (nav, lists, dashboard app tiles).

---

## Related docs

- [GROUP_SPACE_PROJECT_PLAN.md](GROUP_SPACE_PROJECT_PLAN.md) — nav item **Чат**
- [USABILITY_TESTING.md](../USABILITY_TESTING.md) — regression after nav change
