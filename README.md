# Powercoders Learning Journey Hub (PowerHUB)

A web platform for Powercoders bootcamp participants to track their learning journey.

**Branch `integration`:** greenfield rebuild — infrastructure skeleton only. Business apps are added one by one.

## Status

| Layer | State |
|-------|--------|
| Structure | `backend/` + `frontend/` |
| Docker | PostgreSQL 17, Redis, web, Celery worker |
| `accounts` | Custom User (email login, roles, profile) |
| Next | `cohorts`, then dev users command |

## Quick start

See [SETUP.md](SETUP.md) for full instructions.

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000 — health check at http://localhost:8000/health/

## Planned apps (in order)

1. ~~`accounts` — custom User, auth, roles~~ ✓
2. `cohorts` — cohorts and groups (+ User.cohort / User.group)
3. `dashboard` — role-based home
4. `journal`, `goals`, `reflections`, `habits`, `wellbeing`
5. `tracker` — task boards
6. `group_space`, `workflows` — collaboration and learning paths

## Project structure

```
backend/          Django apps, config, manage.py
frontend/         templates and static assets
docs/             project documentation
docker-compose.yml
requirements.txt
```
