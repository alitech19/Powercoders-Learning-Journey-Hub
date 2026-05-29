# Powercoders Learning Journey Hub (PowerHUB)

A web platform for Powercoders bootcamp participants to track their learning journey.

**Branch `integration`:** greenfield rebuild — infrastructure skeleton only. Business apps are added one by one.

## Status

| Layer | State |
|-------|--------|
| Structure | `backend/` + `frontend/` |
| Docker | PostgreSQL 17, Redis, web, Celery worker |
| `accounts` | Custom User, 2FA, onboarding middleware, profile |
| `cohorts` | Cohort, Group, GroupTeacher (admin only) |
| Auth (A–G) | Argon2, axes, CSP, 2FA, onboarding gates, Redis sessions, JSON logs — see [AUTH_ROADMAP](docs/AUTH_ROADMAP.md) |
| Dev seed | `backend/dev/seed.yaml` + quick login — **remove from codebase before prod** ([checklist](docs/PRODUCTION_CHECKLIST.md)) |
| Next | `workflows` — see [APPS_ROADMAP](docs/APPS_ROADMAP.md) |

## Quick start

See [SETUP.md](SETUP.md) for full instructions.

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000 — health check at http://localhost:8000/health/

## Planned apps (customer priority → nav order)

See [docs/APPS_ROADMAP.md](docs/APPS_ROADMAP.md) for the full checklist.

1. ~~`accounts`, `cohorts`, auth, dev seed~~ ✓
2. **`home`** — placeholder hub until dashboard replaces it
3. `workflows` → `goals` → `tracker` (Tasks) → `reflections` / `wellbeing` → `journal` → `habits` → `group_space` (Group) → Resources
4. **`dashboard`** — last; replaces `home` as `/`

App names may be split or renamed during port (Ali split vs django-test `growth`).

## Project structure

```
backend/          Django apps, config, manage.py
frontend/         templates and static assets
docs/             project documentation
docker-compose.yml
requirements.txt
```
