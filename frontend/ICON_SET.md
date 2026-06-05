# PowerHUB volumetric icons

One tile style app-wide: duotone SVG glyph inside a filled rounded box with `shadow-sm`.

## Usage

```django
{% load icon_tags %}
{% volumetric_icon "tasks" size="md" variant="brand" %}
```

Glyphs live in `frontend/templates/includes/icons/_glyph.html` (two-layer `currentColor` fills).

## Sizes (4)

| Size | Tile | Glyph |
|------|------|-------|
| `xs` | 24×24 `rounded-lg` | ~58% SVG — nav dropdown rows |
| `sm` | 32×32 `rounded-lg` | ~58% SVG — navbar bell, cards |
| `md` | 40×40 `rounded-xl` | ~58% SVG — list headers (default) |
| `lg` | 48×48 `rounded-xl` | ~58% SVG — empty states, featured tiles |

## Variants

| Variant | Use |
|---------|-----|
| `brand` | Primary crimson tile `#B23149` + white glyph (default) |
| `cream` | `bg-white/80` on cream dashboard/list cards |
| `soft` | `bg-[#F5EDE0]` — empty states, secondary tiles |
| `nav` | `bg-gray-100` — navbar notifications |

## Icon keys

Defined in `backend/config/icon_map.py` (`ICON_KEYS`). Stable keys:

`workflows`, `tasks`, `goals`, `reflections`, `journal`, `habits`, `chat`, `resources`, `learning`, `wellbeing`, `notifications`, `cohorts`, `users`, `mail`, `alert`, `profile`, `lock`

URL → key mapping: `URL_ICON_KEYS` (nav dropdown).

## Migration status

- [x] Component + SVG glyphs + docs
- [x] Navbar notifications, nav dropdown children
- [x] List empty states (tasks, goals, habits, reflections, journal, workflows, group chat, cohorts, users)
- [x] Dashboard tiles + onboarding checklist (`icon_key` from backend)
- [x] Welcome/onboarding tutorial feature cards
- [x] Confirm-delete headers (`_delete_confirm_icon.html`)
- [x] Login / 2FA lock tile

## Justified outline SVG (functional UI)

Keep minimal stroke icons only where volumetric tiles would add noise:

- **Navigation affordances** — back/next arrows, chevrons, expand toggles (welcome wizard, checklist accordion)
- **Inline actions** — `+` / upload on staff list buttons (cohort import, add user); text labels carry meaning
- **Status affordances** — checkmarks on completed checklist steps, milestone toggles, progress rings
- **User content** — journal mood emoji, chat reactions, etc.

Do not add new flat outline Heroicons for product chrome. User-generated emoji stays as-is.
