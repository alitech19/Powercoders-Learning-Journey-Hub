# PowerHUB — Setup Guide

Local development for PowerHUB: Django, PostgreSQL 17, Redis, Celery (five Compose services).

Related: [TESTING.md](TESTING.md) · [DEPLOY.md](DEPLOY.md) (Render tester) · [README](../README.md)

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- Git

## 1. Clone and switch branch

```bash
git clone <REPO_URL>
cd Powercoders-Learning-Journey-Hub
git checkout integration
```

## 2. Environment file

```bash
cp .env.example .env
```

Edit `.env` if needed. Defaults work for local Docker development.

| Variable | Purpose |
|----------|---------|
| `POSTGRES_*` | Database connection |
| `REDIS_URL` | Cache and Celery broker |
| `SECRET_KEY` | Django secret (change in production) |
| `DEBUG` | `True` for local dev |
| `ENABLE_DEV_SEED` | `true` to load test users from `backend/dev/seed.yaml` (default **False** in code) |
| `CREATE_DEV_SUPERUSER` | `true` to run `create_dev_superuser` on Docker web start (default **false**; set in `.env.example` for local dev) |
| `DJANGO_SUPERUSER_*` | Credentials for dev superuser when `CREATE_DEV_SUPERUSER=true` |

> **Production:** before go-live, **remove dev-user code from the repository** (not just disable env flags). See [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).

## 3. Start services

```bash
docker compose up --build
```

This starts five services:

| Service | Role |
|---------|------|
| `db` | PostgreSQL 17 |
| `redis` | Cache + Celery message broker |
| `web` | Django (`migrate`, `collectstatic`, optional dev superuser/seed, `runserver`) |
| `worker` | Celery worker (runs tasks) |
| `beat` | Celery beat (`django-celery-beat` — schedules in Django admin) |

On first run, migrations run automatically.

On first run: migrations; dev superuser if `CREATE_DEV_SUPERUSER=true` and `DJANGO_SUPERUSER_*` set; dev seed if `ENABLE_DEV_SEED=true`.

## 4. Login

Open http://localhost:8000/account/login/ (redirect from `/accounts/login/` also works).

- **Quick login panel** (when `ENABLE_DEV_SEED=true`): cohort cards with one-click buttons for admin, teachers, and students.
- **Normal login**: email + password — full production flow (axes lockout, 2FA for staff, privacy, welcome).
- **Seed passwords**: `backend/dev/seed.yaml` or superuser credentials from `.env`.

Test users are defined in `backend/dev/seed.yaml` (not in `.env`).

### Cohorts and groups (admin)

All cohort/group setup is in Django admin:

1. **Cohorts** — create a cohort (name, dates, status); add **Groups** inline on the same page
2. **Groups** — open a group to assign **Group teachers** (teachers only, via `GroupTeacher`)
3. **Users** — set **cohort** and **group** on **students** only; cohort auto-syncs from group

Teachers are linked to groups via **Group teachers**, not via fields on the user record.

## 5. Verify

| URL | Expected |
|-----|----------|
| http://localhost:8000/ | Home page |
| http://localhost:8000/health/ | `{"status": "ok"}` |
| http://localhost:8000/account/login/ | 2FA login + dev quick-login panel (if enabled) |
| http://localhost:8000/accounts/profile/ | Profile (after login) |
| http://localhost:8000/admin/ | Django admin |

### Celery worker and beat

```bash
docker compose logs worker
docker compose logs beat
```

Worker should show `celery@... ready.` Beat should show scheduler started (no periodic tasks until you add them in admin or [TODO.md](TODO.md)).

**Periodic schedules:** Django admin → **Periodic tasks** (after `migrate` creates `django_celery_beat` tables).

Test the ping task:

```bash
docker compose exec web python manage.py shell -c "
from config.tasks import ping
result = ping.delay()
print(result.get(timeout=10))
"
```

Expected output: `pong`

## Common commands

```bash
# Stop all services (containers keep named volumes)
docker compose down

# Stop and remove containers + compose network (recommended after local tests)
docker compose down --remove-orphans

# Stop and wipe Postgres volume (fresh DB on next up)
docker compose down -v --remove-orphans

# Postgres only (e.g. you ran `docker compose up -d db` for host tests)
docker compose stop db
docker compose rm -f db

# Run migrations manually
docker compose exec web python manage.py migrate

# Django shell
docker compose exec web python manage.py shell

# View logs
docker compose logs -f web
docker compose logs -f worker
```

Host tests and coverage: [TESTING.md](TESTING.md).

## Local development without Docker

Requires Python 3.12+, PostgreSQL 17, and Redis running locally.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set POSTGRES_HOST=localhost and REDIS_URL=redis://localhost:6379/0 in .env

cd backend
python manage.py migrate
python manage.py runserver
```

Celery worker (separate terminal):

```bash
cd backend
celery -A config worker --loglevel=info
```

## Troubleshooting

**Port 8000 already in use**

Change the port in `docker-compose.yml`: `'8001:8000'`

**Database connection refused**

Wait for the `db` healthcheck to pass, or run `docker compose ps` and check service status.

**PostgreSQL version mismatch after upgrade**

If logs show `database files are incompatible with server` (e.g. upgraded from 16 to 17), reset the volume:

```bash
docker compose down -v
docker compose up --build
```

This deletes local database data. **Required** when switching to `AUTH_USER_MODEL = accounts.User` for the first time.

**Worker not processing tasks**

Ensure `redis` is healthy and `CELERY_BROKER_URL` in `.env` matches (`redis://redis:6379/0` inside Docker).

**`collectstatic` warnings**

Normal on first build. Static files are collected to `frontend/staticfiles/` (gitignored).

## Tester deploy (Render)

Shared environment for QA and usability testing — **not** production.

1. Use Git branch **`deploy`** (merge from `integration` when ready).
2. Follow **[DEPLOY.md](DEPLOY.md)** (Gunicorn, Whitenoise, env vars, web + worker + beat).

## Production deploy

**Before go-live**, **remove dev-user functionality from the codebase** and complete [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md):

- Delete `backend/dev/`, seed commands, quick-login views/templates, and related settings
- Production Docker command: `migrate` + `collectstatic` + app server only
- Create admin manually: `docker compose exec web python manage.py createsuperuser` (on the production host)

Setting `ENABLE_DEV_SEED=false` alone is **not** sufficient for production.

## Tests

See **[TESTING.md](TESTING.md)**.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR: migrate, migration check, then `manage.py test <app>` per business app (sequential steps).

## Related documentation

| Doc | Topic |
|-----|--------|
| [TESTING.md](TESTING.md) | Automated tests |
| [DEPLOY.md](DEPLOY.md) | Render (tester) |
| [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) | Production go-live |
| [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md) | Incidents |
| [TODO.md](TODO.md) | Beat / Slack follow-ups |
