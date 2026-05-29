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
| Next | `dashboard` |

## Quick start

See [SETUP.md](SETUP.md) for full instructions.

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000 — health check at http://localhost:8000/health/

## Planned apps (in order)

1. ~~`accounts` — custom User, auth, roles~~ ✓
2. ~~`cohorts` — cohorts, groups, group teachers (admin)~~ ✓
3. ~~`create_dev_users` — demo users with cohort/group assignments~~ ✓ (see `backend/dev/seed.yaml`)
4. `dashboard` — role-based home
5. `journal`, `goals`, `reflections`, `habits`, `wellbeing`
6. `tracker` — task boards
7. `group_space`, `workflows` — collaboration and learning paths

## Project structure

```
backend/          Django apps, config, manage.py
frontend/         templates and static assets
docs/             project documentation
docker-compose.yml
requirements.txt
```
