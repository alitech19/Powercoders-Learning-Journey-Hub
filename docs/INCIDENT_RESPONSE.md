# Incident Response Runbook

What to do when PowerHUB is degraded or unavailable.

**Environments:** local Docker ([SETUP.md](SETUP.md)), tester/staging on Render ([DEPLOY.md](DEPLOY.md)), future production.

---

## Quick reference

### Local Docker

| What | Where |
|------|--------|
| Application logs | `docker compose logs -f web` |
| Worker logs | `docker compose logs -f worker` |
| Beat logs | `docker compose logs -f beat` |
| Container status | `docker compose ps` |
| Database shell | `docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB` |
| Django shell | `docker compose exec web python manage.py shell` |
| System check | `docker compose exec web python manage.py check` |

### Render (tester / staging)

| What | Where |
|------|--------|
| Web logs | Render dashboard → **powerhub-web** → Logs |
| Worker / Beat | Same for **powerhub-worker**, **powerhub-beat** |
| Shell | Web service → **Shell** → `cd backend` |
| Migrations | Release command or Shell: `python manage.py migrate` |
| Health | `https://<host>/health/` |

---

## Severity levels

| Level | Definition | Target response |
|-------|------------|-----------------|
| **P1** | Platform down — no one can log in | Immediate |
| **P2** | Core feature broken (journal, reflections, tasks, dashboard) | Within 1 hour |
| **P3** | Minor degradation, workaround exists | Within 24 hours |
| **P4** | Cosmetic or low impact | Next release |

---

## Common incidents

### 1. Site unreachable (502 / connection refused)

**Symptoms:** 502, `ERR_CONNECTION_REFUSED`, timeout.

**Docker:**

```bash
docker compose ps
docker compose logs --tail=50 web
docker compose restart web
# if crash loop:
docker compose down && docker compose up --build
```

**Render:** check web service **Events** (deploy failed?), **Logs** (Gunicorn crash), verify start command uses `$PORT`.

**Common causes:** missing env var, migration error on boot, wrong `ALLOWED_HOSTS`, port conflict locally.

---

### 2. Database connection errors

**Symptoms:** `OperationalError`, 500 on every page.

**Docker:**

```bash
docker compose ps
docker compose logs --tail=30 db
docker compose exec db pg_isready -U $POSTGRES_USER -d $POSTGRES_DB
```

Inside Docker, `POSTGRES_HOST` must be `db`, not `localhost`.

**Render:** use Postgres **internal** hostname; confirm `POSTGRES_*` match the attached database.

---

### 3. Migrations broken / “column does not exist”

```bash
# Docker
docker compose exec web python manage.py showmigrations
docker compose exec web python manage.py migrate
```

**Dev only** (destroys data):

```bash
docker compose down -v && docker compose up --build
```

**Render / production:** do **not** `down -v`. Fix forward with migrations or restore from backup.

---

### 4. Static files / CSS missing

**Docker:**

```bash
docker compose exec web python manage.py collectstatic --noinput
docker compose restart web
```

**Render:** ensure build runs `collectstatic` and Whitenoise is enabled on the `deploy` branch ([DEPLOY.md](DEPLOY.md)).

---

### 5. Celery / email / Slack not working

**Symptoms:** welcome mail missing, Slack digest silent, notifications not emailed.

```bash
# Docker
docker compose logs --tail=50 worker
docker compose logs --tail=50 beat
docker compose exec redis redis-cli ping   # PONG
docker compose restart worker beat
```

**Render:** check worker and beat services are **running** (not suspended). Verify `CELERY_BROKER_URL` / `REDIS_URL`. Register periodic tasks in admin — [plans/TODO.md](plans/TODO.md).

---

### 6. 2FA / login lockout

**Brute-force (django-axes):**

```bash
docker compose exec web python manage.py axes_reset_ip --ip <IP>
# or in shell:
# AccessAttempt.objects.filter(username='user@example.com').delete()
```

**Lost 2FA device** (admin recovery):

```bash
docker compose exec web python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> u = get_user_model().objects.get(email='user@example.com')
>>> u.totpdevice_set.all().delete()
```

---

### 7. Disk / media full or uploads failing

**Docker:** check `backend/media/` (group files, avatars). `docker system df` / `docker system prune`.

**Render:** local media is ephemeral; large uploads may need object storage ([SCALING_ROADMAP.md](SCALING_ROADMAP.md)).

---

## After resolving

1. Verify the affected flow end-to-end (login → dashboard → feature).
2. Scan logs for remaining errors.
3. Brief note to the team: what broke, root cause, fix.
4. Recurring issues → add a line to [SETUP.md](SETUP.md) troubleshooting or this file.

---

## Escalation

If not resolved within the target time:

1. Check `/admin/` for data integrity.
2. Restore DB from latest backup (production); on Render use Postgres backups/snapshots if enabled.
3. Contact the **repository maintainer** listed in the GitHub repo or your team lead.

Do not post credentials or `SECRET_KEY` in public channels.
