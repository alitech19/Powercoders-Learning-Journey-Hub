# Powercoders Learning Journey Hub (PowerHUB)

A web platform for Powercoders bootcamp participants to track their learning journey.

**Branch `integration`:** greenfield rebuild with nav apps, dashboard, and in-app help shipped; ops/admin backports from `origin/Ali` remain.

## Status

| Layer | State |
|-------|--------|
| Structure | `backend/` + `frontend/` |
| Docker | PostgreSQL 17, Redis, web, Celery worker + beat |
| Nav apps | Workflows, Goals, Tasks, Reflections, Journal, Habits, Group, Resources |
| `dashboard` | Role-based home at `/` |
| `info` | Contextual help (ⓘ) per app |
| `accounts` | Custom User, 2FA, onboarding middleware, profile |
| `cohorts` | Cohort, Group, GroupTeacher (admin only; in-app CRUD still TODO) |
| Auth | Argon2, axes, CSP, 2FA, onboarding gates, Redis sessions, JSON logs |
| Dev seed | `backend/dev/seed.yaml` + quick login — **remove from codebase before prod** ([checklist](docs/PRODUCTION_CHECKLIST.md)) |
| Next | [APP_PLAN](docs/APP_PLAN.md) — active: [TODO](docs/TODO.md) |

## Quick start

See [SETUP.md](SETUP.md) for full instructions.

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000 — health check at http://localhost:8000/health/

## Roadmap

Customer-facing apps are integrated. Remaining work (CI, admin UI, Slack/email, tests, ops docs) is listed in [docs/APP_PLAN.md](docs/APP_PLAN.md). Resource file storage: [docs/RESOURCE_FILE_STORAGE.md](docs/RESOURCE_FILE_STORAGE.md).

## Project structure

```
backend/          Django apps, config, manage.py
frontend/         templates and static assets
docs/             project documentation
docker-compose.yml
requirements.txt
```
