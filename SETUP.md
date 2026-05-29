# PowerHUB — Setup Guide

Infrastructure skeleton for the `integration` branch: Django, PostgreSQL 17, Redis, Celery.

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

## 3. Start services

```bash
docker compose up --build
```

This starts four services:

| Service | Role |
|---------|------|
| `db` | PostgreSQL 17 |
| `redis` | Cache + Celery message broker |
| `web` | Django (`migrate`, `collectstatic`, `runserver`) |
| `worker` | Celery worker |

On first run, migrations run automatically.

## 4. Create admin user

In a new terminal:

```bash
docker compose exec web python manage.py createsuperuser
```

Uses Django's default `auth.User` until the `accounts` app is added.

## 5. Verify

| URL | Expected |
|-----|----------|
| http://localhost:8000/ | Home page — "Infrastructure skeleton is ready" |
| http://localhost:8000/health/ | `{"status": "ok"}` |
| http://localhost:8000/admin/ | Django admin (after superuser) |

### Celery worker

```bash
docker compose logs worker
```

Should show `celery@... ready.`

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
# Stop services
docker compose down

# Stop and remove database volume (fresh start)
docker compose down -v

# Run migrations manually
docker compose exec web python manage.py migrate

# Django shell
docker compose exec web python manage.py shell

# View logs
docker compose logs -f web
docker compose logs -f worker
```

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

This deletes local database data.

**Worker not processing tasks**

Ensure `redis` is healthy and `CELERY_BROKER_URL` in `.env` matches (`redis://redis:6379/0` inside Docker).

**`collectstatic` warnings**

Normal on first build. Static files are collected to `frontend/staticfiles/` (gitignored).

## Next step

Add the `accounts` app — custom User model with email login, roles, and display name. This must happen before any other app that references users.
