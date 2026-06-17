# Deploy — Render (tester / staging)

This guide is for a **shared tester environment** on [Render](https://render.com), not production go-live. Production hardening is in [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).

Related: [SETUP.md](SETUP.md) (local) · [TESTING.md](TESTING.md) · [README](../README.md)

**Branch model:** develop on **`main`** (local Docker — [SETUP.md](SETUP.md)). When ready for testers, merge `main` → **`deploy`** and push; Render services track branch **`deploy`**.

```bash
git checkout deploy
git pull origin deploy
git merge main
git push origin deploy
```

App code is the same on both branches; Render uses **Start commands** and **`.env.render-test.example`**, not `docker compose`.

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

Profile photos are stored in the database (base64). Group chat attachments and other uploads still use `MEDIA_ROOT` on disk. Render web disks are **ephemeral** — those file uploads can disappear on redeploy. For tester QA this is often acceptable; for stable files use S3 later ([SCALING_ROADMAP.md](SCALING_ROADMAP.md)).

### Creating users on Render

The dev-seed / quick-login mechanism has been **removed from the codebase**. Create the admin via the Render **Shell** (`python manage.py createsuperuser`), then add users from **Administration → Users** or CSV import. New users get a temporary password (emailed when SMTP is configured — otherwise it appears in the create-user UI) and set their own on first login.

---

## Tester profile — `DEBUG=True` (default for this deploy)

Template: [`.env.render-test.example`](../.env.render-test.example).

| Variable | Value |
|----------|--------|
| `DEBUG` | `True` |
| `ALLOWED_HOSTS` | `your-app.onrender.com` (no `https://`) |
| `CSRF_TRUSTED_ORIGINS` | `https://your-app.onrender.com` |
| `SITE_URL` | `https://your-app.onrender.com` |

Emails go to **Render logs** only unless SMTP is configured. **Not** for production — treat the URL as internal QA.

**Start command (web)** — use [`scripts/render-web-start.sh`](../scripts/render-web-start.sh) (see [§3 Web service](#3-web-service)): runs `migrate`, then Gunicorn.

Login: `/account/login/` — create the admin first via the Render **Shell** (`python manage.py createsuperuser`).

### Alternative — `DEBUG=False` (stricter staging)

No dev panel; create users manually after deploy.

| Variable | Value |
|----------|--------|
| `DEBUG` | `False` |
| `ENABLE_DEV_SEED` | `false` |
| `CREATE_DEV_SUPERUSER` | `false` |

**Start command:** same `render-web-start.sh` (migrate + Gunicorn).  
Then Shell: `cd backend && python manage.py createsuperuser`.

---

## Git workflow

```bash
git checkout deploy
git pull origin deploy
git merge main   # or cherry-pick specific commits
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

**Option A (recommended):** Web service → **Connections** → link `powerhub-db` → Render adds **`DATABASE_URL`**. The app reads it automatically (Internal URL).

**Option B:** Set each variable manually (from Postgres → **Connect** → Internal):

| Variable | Source |
|----------|--------|
| `POSTGRES_DB` | database name |
| `POSTGRES_USER` | user |
| `POSTGRES_PASSWORD` | password |
| `POSTGRES_HOST` | hostname (e.g. `dpg-xxxxx-a`) — **never** `localhost` on Render |
| `POSTGRES_PORT` | `5432` |

If login shows `connection to 127.0.0.1:5432 refused`, Django is using the default host `localhost` — **`DATABASE_URL` and `POSTGRES_HOST` are not set on the web service** (or the deploy branch lacks `DATABASE_URL` support in `settings.py`). Fix env, redeploy, then check `https://<host>/health/?db=1` — `db_host` must be `dpg-…`, not `localhost`.

### 2. Redis

1. **New → Key Value** → name `powerhub-redis`.
2. Copy **Internal Redis URL** → set `REDIS_URL` and `CELERY_BROKER_URL` to the same value.

### 3. Web service

1. **New → Web Service** → connect repo.
2. **Branch:** **`deploy`** — not `main`. (`main` is only an initial stub; no `requirements.txt` there.)
3. **Root Directory:** leave **empty** (project root must contain `requirements.txt`, `backend/`, `runtime.txt`).
4. **Runtime:** Native **Python** (not Docker) — see build/start below.

Repo includes **`runtime.txt`** (`python-3.12.12`) so Render does not default to Python 3.14.

**Build command:**

```bash
pip install -r requirements.txt && cd backend && python manage.py collectstatic --noinput
```

**Start command** — free/starter plans have **no Pre-deploy**. Run migrate in **Start** (or use `scripts/render-web-start.sh`):

```bash
chmod +x scripts/render-web-start.sh && ./scripts/render-web-start.sh
```

Inline equivalent (only if not using the script):

```bash
cd backend && python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

Prefer **`render-web-start.sh`**: runs `migrate` then Gunicorn. `migrate` on every restart is normal for QA. **Do not** put `migrate` in **Build** — build has no access to the internal database.

(Render sets `$PORT`.)

**Health check path:** `/health/`

### 4. Celery worker

1. **New → Background Worker** → same repo, branch **`deploy`**.
2. **Build command:** `pip install -r requirements.txt` (no `collectstatic`).
3. **Start command** (low memory — required on small Render plans):

```bash
cd backend && celery -A config worker --loglevel=info --concurrency=1
```

4. **Environment:** same group as web, plus `CELERY_WORKER_CONCURRENCY=1`.

Default Celery prefork uses ~16 processes; each loads Django → **OOM** → restart loop (you never see `celery@… ready.` in logs).

### 5. Celery beat

1. **New → Background Worker** → same repo, branch **`deploy`**.
2. **Build command:** `pip install -r requirements.txt`
3. **Start command** (migrate first — no pre-deploy on free tier):

```bash
chmod +x scripts/render-beat-start.sh && ./scripts/render-beat-start.sh
```

Or inline:

```bash
cd backend && python manage.py migrate --noinput && celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

5. **Environment:** same group as web (all `POSTGRES_*`, `REDIS_URL`, `SECRET_KEY`, `DEBUG`, …).
6. **Instance count: 1** only — never scale beat horizontally.
7. **Optional for first QA:** suspend/delete the beat service until you need scheduled jobs. Web + worker are enough for manual testing.

**Healthy logs** should continue past `Configuration ->` with something like `beat: Starting...` / `DatabaseScheduler: Schedule changed.` If the instance **restarts** right after `maxinterval -> 5.00 seconds`, open **Logs** (full stderr) for `OperationalError`, `django.db`, or OOM — usually missing migrate on shared Postgres, missing `POSTGRES_*` on beat, or Python 3.14 (use `PYTHON_VERSION=3.12.12` / `runtime.txt`).

**Reminder schedule** is no longer configured via `.env`. After migrate, open **Administration → Notifications** (`/admin-config/notifications/`) to enable deadline reminders and the weekly reflection digest — saving syncs Celery Beat tasks automatically. Hourly/daily user digest tasks are registered from `CELERY_BEAT_SCHEDULE` in settings.

### 6. Migrations without Pre-deploy (free tier)

Paid Render can use **Pre-deploy** for migrate only. On **free** plans use **Start command** (section 3) or **Shell** once:

```bash
cd backend && python manage.py migrate --noinput && python manage.py createsuperuser
```

---

## Environment variables (web + worker + beat)

Create one **Environment Group** in Render and attach it to all three services. Use a [tester profile](#tester-profile--debugtrue-default-for-this-deploy) above or the table below.

| Variable | Notes |
|----------|--------|
| `SECRET_KEY` | Long random string; never commit |
| `POSTGRES_*` | From Render Postgres (**internal** host) |
| `REDIS_URL` / `CELERY_BROKER_URL` | Internal Redis URL (`rediss://` if TLS) |
| Slack (OAuth + staff webhook) | **Administration → Slack integration** in the app (encrypted in DB) — not `.env` |
| `EMAIL_HOST`, … | Only if using SMTP instead of console backend |

**Removed:** `REFLECTION_REMINDER_HOUR`, `REFLECTION_REMINDER_MINUTE`, `REFLECTION_REMINDER_DAY` — use **Administration → Notifications** instead.

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
5. **Notifications:** open **Administration → Notifications** and confirm deadline / reflection settings. Check **Django admin → Periodic tasks** for `Hourly deadline reminders`, `Weekly missing-reflections digest`, and digest dispatch tasks ([plans/TODO.md](plans/TODO.md)).
6. Smoke-test: journal, reflection, group post with `@mention`, profile → export data, notifications bell.

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
| `No such file: requirements.txt` | **Branch** must be `deploy`. **Root Directory** must be empty. |
| Python 3.14 / wrong version | Add `runtime.txt` at repo root or env `PYTHON_VERSION=3.12.12` |
| `We don't have access to your repo` | GitHub: Settings → Applications → authorize Render; or deploy with public repo access |
| 502 / app not listening | Start command uses `$PORT` and `gunicorn` |
| DisallowedHost | `ALLOWED_HOSTS` includes exact hostname |
| CSRF failed on login | `CSRF_TRUSTED_ORIGINS` includes `https://...` |
| 500 DB errors / `127.0.0.1:5432 refused` | Set **`DATABASE_URL`** (link Postgres) or `POSTGRES_HOST` = internal hostname (not localhost) on **web, worker, beat** |
| Celery tasks never run | Worker service running; `CELERY_BROKER_URL` set; check worker logs |
| Worker restart loop, no `ready` | Set `--concurrency=1` and `CELERY_WORKER_CONCURRENCY=1`; upgrade plan or reduce memory |
| Beat restart loop after `maxinterval` | **Pre-deploy:** `migrate` on beat service; full `POSTGRES_*` env; `PYTHON_VERSION=3.12.12`; 1 instance; or **suspend beat** until periodic tasks needed |
| Beat schedule missing | Beat service running; task registered in admin |
| Static files 404 | Whitenoise middleware + `collectstatic` in build |
| Uploads vanished | Expected on redeploy without persistent disk/S3 |

More incidents: [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md).

---

## Production vs tester

| | Tester (this doc) | Production |
|--|-------------------|------------|
| Branch | `deploy` | `main` or release tag |
| Dev quick-login / seed | Removed from codebase | Removed from codebase |
| `DEBUG` | May be `True` briefly | `False` |
| Email | Real SMTP recommended | Real SMTP required |
| Scaling detail | [SCALING_ROADMAP.md](SCALING_ROADMAP.md) | Same + backups, monitoring |

---

## Related docs

- Local setup: [SETUP.md](SETUP.md)
- Tests: [TESTING.md](TESTING.md)
- Ops runbook: [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)
- UX test plan: [USABILITY_TESTING.md](USABILITY_TESTING.md)
