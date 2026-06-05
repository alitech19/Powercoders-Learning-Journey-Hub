# PowerHUB volumetric icons

One tile style app-wide: emoji glyph inside a filled rounded box with `shadow-sm`.

## Usage

```django
{% load icon_tags %}
{% volumetric_icon "tasks" size="md" variant="brand" %}
```

## Sizes (4)

| Size | Tile | Glyph |
|------|------|-------|
| `xs` | 24×24 `rounded-lg` | `text-xs` — nav dropdown rows |
| `sm` | 32×32 `rounded-lg` | `text-sm` — navbar bell |
| `md` | 40×40 `rounded-xl` | `text-lg` — cards, list headers (default) |
| `lg` | 48×48 `rounded-xl` | `text-xl` — empty states, featured tiles |

## Variants

| Variant | Use |
|---------|-----|
| `brand` | Primary crimson tile `#B23149` + white glyph (default) |
| `cream` | `bg-white/80` on cream dashboard/list cards |
| `soft` | `bg-[#F5EDE0]` — empty states, secondary tiles |
| `nav` | `bg-gray-100` — navbar notifications |

## Icon keys

Defined in `backend/config/icon_map.py` (`ICON_MAP`). Stable keys:

`workflows`, `tasks`, `goals`, `reflections`, `journal`, `habits`, `chat`, `resources`, `learning`, `wellbeing`, `notifications`, `cohorts`, `users`, `mail`, `alert`

URL → key mapping: `URL_ICON_KEYS` (nav dropdown).

## Migration status

- [x] Component + map + docs
- [x] Navbar notifications, nav dropdown children
- [x] List empty states (tasks, goals, habits, reflections, journal, workflows, group chat, cohorts)
- [x] Dashboard (`dashboard/dashboard.html`) — student tiles, teacher quick links, admin management cards

Do not add new flat outline Heroicons for product chrome. User-generated emoji (journal mood, etc.) stays as-is.
