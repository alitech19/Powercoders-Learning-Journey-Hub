# PowerHUB — Setup Guide

Local development for PowerHUB: Django, PostgreSQL 17, Redis, Celery (five Compose services).

Related: [TESTING.md](TESTING.md) · [DEPLOY.md](DEPLOY.md) (Render only) · [README](../README.md)

## Local vs Render

| | **`integration` branch (this guide)** | **`deploy` branch on Render** |
|--|--------------------------------------|-------------------------------|
| Config | [`.env.example`](../.env.example) → `.env` | [`.env.render-test.example`](../.env.render-test.example) in Render dashboard |
| Start | `docker compose up` → **runserver** | Gunicorn + `scripts/render-web-start.sh` (migrate in start on free tier) |
| Database | `POSTGRES_HOST=db` | `DATABASE_URL` or internal `POSTGRES_HOST` |
| Do not use locally | `scripts/render-*.sh`, Render env template | — |

Code is shared after merging `integration` → `deploy`; only **how you run** the app differs.

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

> **Note:** dev-user seeding and the quick-login panel have been **removed from the codebase**. Create accounts with `createsuperuser` and the in-app **Administration → Users**. See [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).

## 3. Start services

```bash
docker compose up --build
```

This starts six services:

| Service | Role |
|---------|------|
| `db` | PostgreSQL 17 |
| `redis` | Cache + Celery message broker |
| `migrate` | One-shot `locked_migrate` (runs once per `up`, then exits) |
| `web` | Django (`collectstatic`, `runserver`) — starts **after** migrate |
| `worker` | Celery worker (runs tasks) |
| `beat` | Celery beat (`django-celery-beat` — schedules in Django admin) |

On first run, the **`migrate`** service applies migrations automatically. Do **not** run `manage.py migrate` at the same time as `docker compose up` — use `locked_migrate` if you need to migrate manually later.

### Frontend (`integration` branch)

Templates use **CDN** Tailwind, HTMX, and Alpine (`frontend/templates/base.html`). Brand colours: `#B23149` (primary), `#343534` (charcoal). Compiled CSS and self-hosted JS are planned before production — [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).

Navbar: **Learning** / **Wellbeing** dropdowns, **Group Space**, **Resources**; **Administration** (admin only, right). Per-page help is the **ⓘ** button in content (`info` app), not in the navbar.

## 4. Login

Open http://localhost:8000/account/login/ (redirect from `/accounts/login/` also works).

Create an admin first:

```bash
docker compose exec web python manage.py createsuperuser
```

Then log in with email + password — the full production flow (axes lockout, 2FA for staff, privacy, welcome tutorial). First login is gated by `WelcomeMiddleware` until `welcome_seen` is set. Create further users from **Administration → Users** (or CSV import); each new user gets a temporary password and is forced to change it on first login.

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
| http://localhost:8000/account/login/ | Email + password login (2FA for staff) |
| http://localhost:8000/accounts/profile/ | Profile (after login) |
| http://localhost:8000/admin/ | Django admin |

### Celery worker and beat

```bash
docker compose logs worker
docker compose logs beat
```

Worker should show `celery@... ready.` Beat should show scheduler started (no periodic tasks until you add them in admin or [plans/TODO.md](plans/TODO.md)).

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

Complete [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md). The dev-user mechanism (seed, quick-login, `create_dev_superuser`) has already been **removed from the codebase**. For go-live:

- Production Docker command: `migrate` + `collectstatic` + app server only
- Set `DEBUG=False` with a strong `SECRET_KEY`, and configure SMTP so real users receive email
- Create the admin manually: `docker compose exec web python manage.py createsuperuser` (on the production host)

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
| [plans/TODO.md](plans/TODO.md) | Beat / Slack follow-ups |
