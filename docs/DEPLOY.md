# Deploy — Render (tester / staging)

This guide is for a **shared tester environment** on [Render](https://render.com), not production go-live. Production hardening is in [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).

Related: [SETUP.md](SETUP.md) (local) · [TESTING.md](TESTING.md) · [README](../README.md)

**Branch model:** maintain a long-lived Git branch `deploy` on GitHub. Merge into `deploy` only what you want on the tester URL (e.g. from `integration`). Connect Render services to **`deploy`**, not `main`.

---

## What you deploy

| Render service | Type | Role |
|----------------|------|------|
| `powerhub-web` | Web Service | Django (Gunicorn), HTTPS URL for testers |
| `powerhub-worker` | Background Worker | Celery worker (email, Slack tasks) |
| `powerhub-beat` | Background Worker | Celery Beat (`django-celery-beat`) |
| `powerhub-db` | PostgreSQL | Database |
| `powerhub-redis` | Key Value (Redis) | Cache, sessions, Celery broker |

Local development stays on Docker Compose — see [SETUP.md](SETUP.md).

---

## Application code (in repo)

These are already in `requirements.txt` and `backend/config/settings.py`:

- **Gunicorn** + **Whitenoise** (`WhiteNoiseMiddleware` after `SecurityMiddleware`, `CompressedStaticFilesStorage`)
- **`CSRF_TRUSTED_ORIGINS`**, secure cookies, and `SECURE_PROXY_SSL_HEADER` when `DEBUG=False`

Run **`collectstatic`** on every web deploy (build command below). Local Docker still uses `runserver`; Render uses Gunicorn.

### Media files (tester env)

Uploaded files (avatars, group chat attachments) use `MEDIA_ROOT` on disk. Render web disks are **ephemeral** — uploads can disappear on redeploy. For tester QA this is often acceptable; for stable files use S3 later ([SCALING_ROADMAP.md](SCALING_ROADMAP.md)).

### Dev seed on Render

`ENABLE_DEV_SEED` only applies when `DEBUG=True` in settings. For a tester host you can either:

- **`DEBUG=True`** only on Render (simplest for seed + quick login; **not** for real production), or  
- **`DEBUG=False`**: create users via Django admin or CSV import; no dev quick-login panel.

Do **not** treat a `DEBUG=True` Render URL as production.

---

## Tester profile — `DEBUG=True` (default for this deploy)

Template: [`.env.render-test.example`](../.env.render-test.example).

| Variable | Value |
|----------|--------|
| `DEBUG` | `True` |
| `ENABLE_DEV_SEED` | `true` |
| `CREATE_DEV_SUPERUSER` | `true` (set strong `DJANGO_SUPERUSER_*` in Render — not the local dev default) |
| `ALLOWED_HOSTS` | `your-app.onrender.com` (no `https://`) |
| `CSRF_TRUSTED_ORIGINS` | `https://your-app.onrender.com` |
| `SITE_URL` | `https://your-app.onrender.com` |

Enables dev **quick-login** panel and loads users from `backend/dev/seed.yaml` on deploy. Emails go to **Render logs** only. **Not** for production — treat the URL as internal QA.

**Release command (web):**

```bash
cd backend && python manage.py migrate --noinput && python manage.py create_dev_superuser && python manage.py seed_dev_data
```

Login: `/account/login/` — quick-login cohort cards (if seed ran) or seed emails from `backend/dev/seed.yaml`.

### Alternative — `DEBUG=False` (stricter staging)

No dev panel; create users manually after deploy.

| Variable | Value |
|----------|--------|
| `DEBUG` | `False` |
| `ENABLE_DEV_SEED` | `false` |
| `CREATE_DEV_SUPERUSER` | `false` |

**Release command:** `cd backend && python manage.py migrate --noinput`  
Then Shell: `python manage.py createsuperuser`.

---

## Git workflow

```bash
git checkout deploy
git pull origin deploy
git merge integration   # or cherry-pick specific commits
# resolve conflicts, run tests locally
git push origin deploy
```

Render auto-deploys when `deploy` is pushed (if auto-deploy is enabled).

**Suggested protection:** require CI green on PRs into `deploy`; only maintainers merge.

---

## Render setup (first time)

### 1. PostgreSQL

1. **New → PostgreSQL** → name `powerhub-db`, region close to users (e.g. Frankfurt).
2. After create, copy **Internal Database URL** (use internal hostname from other Render services).

Map to Django env vars (from Render’s connection fields or by parsing the URL):

| Variable | Source |
|----------|--------|
| `POSTGRES_DB` | database name |
| `POSTGRES_USER` | user |
| `POSTGRES_PASSWORD` | password |
| `POSTGRES_HOST` | hostname (internal) |
| `POSTGRES_PORT` | `5432` |

### 2. Redis

1. **New → Key Value** → name `powerhub-redis`.
2. Copy **Internal Redis URL** → set `REDIS_URL` and `CELERY_BROKER_URL` to the same value.

### 3. Web service

1. **New → Web Service** → connect repo → branch **`deploy`**.
2. **Root directory:** leave empty (repo root).
3. **Runtime:** Docker *or* Python — below assumes **Python** native build.

**Build command:**

```bash
pip install -r requirements.txt && cd backend && python manage.py collectstatic --noinput
```

**Start command:**

```bash
cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

(Render sets `$PORT`.)

**Health check path:** `/health/`

### 4. Celery worker

1. **New → Background Worker** → same repo, branch **`deploy`**.
2. **Start command:**

```bash
cd backend && celery -A config worker --loglevel=info
```

3. Attach the **same environment group** as the web service (DB + Redis vars).

### 5. Celery beat

1. **New → Background Worker** → same repo, branch **`deploy`**.
2. **Start command:**

```bash
cd backend && celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

3. **Only one Beat instance** — do not scale beat horizontally.

### 6. Release command (recommended)

On the **web** service, **Settings → Deploy → Pre-deploy command** (or “Release command”):

```bash
cd backend && python manage.py migrate --noinput
```

Runs before each deploy so the DB schema stays current.

---

## Environment variables (web + worker + beat)

Create one **Environment Group** in Render and attach it to all three services. Use a [tester profile](#tester-profiles-pick-one) above or the table below.

| Variable | Notes |
|----------|--------|
| `SECRET_KEY` | Long random string; never commit |
| `POSTGRES_*` | From Render Postgres (**internal** host) |
| `REDIS_URL` / `CELERY_BROKER_URL` | Internal Redis URL (`rediss://` if TLS) |
| `SLACK_WEBHOOK_URL` | Optional — [TODO.md](TODO.md) |
| `EMAIL_HOST`, … | Only if using SMTP instead of console backend |

**Do not** use weak `DJANGO_SUPERUSER_*` on a public tester URL.

---

## After first deploy

1. Open `https://<your-service>.onrender.com/health/` → `{"status": "ok"}`.
2. **Shell** on web service (Render dashboard → Shell):

   ```bash
   cd backend
   python manage.py createsuperuser
   ```

3. Log in at `/account/login/`, complete 2FA setup for staff accounts.
4. Create cohorts/groups/users via **Admin** or `/accounts/users/` (admin).
5. **Periodic tasks:** Admin → **Periodic tasks** → register `accounts.tasks.notify_missing_reflections` (weekly cron). See [TODO.md](TODO.md).
6. Smoke-test: journal, reflection, group post with resource label, profile → export data, notifications bell.

Share the URL and test accounts with testers via a **private** channel (not in the repo).

---

## Deploy updates

1. Merge to `deploy` → Render rebuilds web (and workers if shared env/build changed).
2. Watch **Logs** on web / worker / beat for migration or import errors.
3. If static/CSS breaks after a frontend change, confirm build ran `collectstatic` and Whitenoise is enabled.

---

## Troubleshooting on Render

| Symptom | Check |
|---------|--------|
| 502 / app not listening | Start command uses `$PORT` and `gunicorn` |
| DisallowedHost | `ALLOWED_HOSTS` includes exact hostname |
| CSRF failed on login | `CSRF_TRUSTED_ORIGINS` includes `https://...` |
| 500 DB errors | `POSTGRES_HOST` is **internal** URL from Render Postgres |
| Celery tasks never run | Worker service running; `CELERY_BROKER_URL` set; check worker logs |
| Beat schedule missing | Beat service running; task registered in admin |
| Static files 404 | Whitenoise middleware + `collectstatic` in build |
| Uploads vanished | Expected on redeploy without persistent disk/S3 |

More incidents: [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md).

---

## Production vs tester

| | Tester (this doc) | Production |
|--|-------------------|------------|
| Branch | `deploy` | `main` or release tag |
| Dev quick-login / seed in repo | Optional with `DEBUG=True` | **Remove code** — [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) |
| `DEBUG` | May be `True` briefly | `False` |
| Email | Real SMTP recommended | Real SMTP required |
| Scaling detail | [SCALING_ROADMAP.md](SCALING_ROADMAP.md) | Same + backups, monitoring |

---

## Related docs

- Local setup: [SETUP.md](SETUP.md)
- Tests: [TESTING.md](TESTING.md)
- Ops runbook: [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)
- UX test plan: [USABILITY_TESTING.md](USABILITY_TESTING.md)
