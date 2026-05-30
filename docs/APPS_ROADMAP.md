# Business apps roadmap (integration branch)

Greenfield port from `origin/Ali` and `origin/django-test`. Apps are added **one at a time** in **customer priority order** — the same order drives the **main navigation** (left → right).

## Hub vs dashboard

| Phase | URL `/` | Role |
|-------|---------|------|
| **Now** | `home` | Placeholder hub — links only to **already integrated** apps (+ profile, admin) |
| **Last** | `dashboard` | Role-based home **replaces `home`**; `LOGIN_REDIRECT_URL` switches to dashboard |

No dead links: nav and home read from a single registry (`config/nav.py`). Entries are enabled only when the app is wired.

## Integration order (customer priority)

Build sequence **2 → 9**, then **dashboard (1)**. Status and names may change during port.

| Build # | App (working name) | Nav label | Source | Status |
|---------|-------------------|-----------|--------|--------|
| 2 | `workflows` | Workflows | Ali | Done |
| 3 | `goals` | Goals | Ali | Done |
| 4 | `tracker` | Tasks | Ali (+ django-test permission ideas) | Pending |
| 5a | `reflections` | Reflections | Ali | Pending |
| 5b | `wellbeing` | Wellbeing | django-test (`growth`) | Pending — same phase as reflections |
| 6 | `journal` | Journal | Ali | Pending |
| 7 | `habits` | Habits | django-test (`growth`) | Pending |
| 8 | `group_space` | Group | Ali | Pending |
| 9 | `group_space` (resources view) | Resources | Ali | Pending — likely same app, separate nav route |
| **1 (last)** | `dashboard` | — (replaces `home` URL) | Ali | Pending |

**Next app to port:** `tracker` (Tasks)

### Not in main nav (by design)

- **`cohorts`** — admin only (done)
- **`accounts`** — profile, onboarding (done); user mgmt UI later
- **`api`** — health/scaffold when needed
- **`dashboard`** — not a nav item; becomes the `/` landing page at the end

## Per-app checklist (each PR)

1. Create `backend/<app>/` (models, views, urls, admin if needed)
2. Templates under `frontend/templates/<app>/`
3. Set `enabled=True` on the matching row(s) in `config/nav.py`
4. Migrations + seed touch-ups if dev users need sample data
5. Home hub + navbar update automatically (same registry)
6. Mark **Done** in the table above

## Rename / split policy

- App package names may differ from nav labels (e.g. `tracker` → "Tasks")
- **Reflections + wellbeing** — one integration phase; keep separate apps if models diverge
- **Resources** — port with `group_space` unless customer wants a standalone app later
- Monolithic django-test `growth` is **not** ported as-is; split per rows above

## Reference

- Auth complete: [AUTH_ROADMAP.md](AUTH_ROADMAP.md)
- Prod dev removal: [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)
