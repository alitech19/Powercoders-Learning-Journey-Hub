# Scaling Roadmap

Current architecture, limits, and phased improvements for PowerHUB.

**Today:** five Docker Compose services locally; tester deploy on Render uses separate web + worker + beat — see [DEPLOY.md](DEPLOY.md). **Production go-live:** [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).

---

## Current state (`main` / `deploy`)

| Service | Role | Limitation |
|---------|------|------------|
| `web` | Django (`runserver` locally; Gunicorn on Render `deploy`) | Not multi-region; workers tuned per host |
| `worker` | Celery | Single process unless scaled on platform |
| `beat` | Celery Beat (`django-celery-beat`) | Must be **one** instance globally |
| `db` | PostgreSQL 17 | No replication/backups in default Compose |
| `redis` | Cache, sessions, broker | No AOF by default in Compose |

Suitable for a **small cohort** (&lt; ~50 users) in a controlled or tester environment. Public production needs Phase 1 minimum.

**Stack highlights:** custom `accounts.User`, 2FA, Argon2, axes, CSP, Redis sessions, HTMX UI, Celery for email/Slack tasks, in-app notifications.

---

## Phase 1 — Before real production

| Action | Why |
|--------|-----|
| Gunicorn (+ Whitenoise for static) | `runserver` is not production-safe |
| `DEBUG=False`, strong `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Security |
| HTTPS (Render provides TLS; self-hosted needs Nginx/Certbot) | Cookies, 2FA, CSP |
| Real SMTP (`EMAIL_*`) | Welcome mail, feedback, notifications |
| Remove dev seed / quick-login from **code** | [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) |
| Daily Postgres backups | Restore path |
| `SITE_URL` + optional `SLACK_WEBHOOK_URL` | Correct links in email/Slack |

**Render tester:** Phase 1 partially covered in [DEPLOY.md](DEPLOY.md); still not a substitute for production checklist.

### Local Compose example (Gunicorn)

After adding `gunicorn` to `requirements.txt`, web command can become:

```yaml
command: >
  sh -c "python manage.py migrate --noinput &&
         python manage.py collectstatic --noinput &&
         gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4"
```

Add Whitenoise in `settings.py` for static without Nginx.

### Self-hosted: Nginx (optional)

Nginx terminates SSL and serves `/static/` and `/media/`; Gunicorn handles Django. See historical Ali notes — only needed if not using Render’s TLS + Whitenoise.

---

## Phase 2 — 50–200 users

| Action | Why |
|--------|-----|
| Tune Gunicorn workers | `2 × CPU + 1`, watch memory |
| Keep Beat as **one** dedicated service | Already split in Compose and Render |
| Redis AOF persistence | Survive broker restarts |
| `CONN_MAX_AGE` on DB | Fewer connection spikes |
| Object storage for `MEDIA_ROOT` | Ephemeral disks (Render) lose uploads |

**Resources:** group chat uploads use **Google Drive** ([GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md)); optional S3 for other `MEDIA_ROOT` use cases later.

---

## Phase 3 — 200+ users / high availability

| Component | Direction |
|-----------|-----------|
| PostgreSQL | Managed (Render Postgres, RDS, Supabase) + backups |
| Redis | Managed (Render KV, Upstash, ElastiCache) |
| Media | S3 / R2 + `django-storages` |
| App | Render scale, Fly.io, or Kubernetes |
| Static | CDN in front of Whitenoise or bucket |
| Reads | Postgres read replica + router (if dashboards heavy) |

Tester URL on Render is a **Phase 1–2 slice** (managed DB/Redis, single web instance) — scale horizontally when metrics demand it.

---

## Monitoring

- **Logs:** JSON to stdout (`config/settings.py` logging) — use Render log stream or `docker compose logs`.
- **Health:** `GET /health/` for load balancers.
- **Optional:** Sentry (`sentry-sdk`), OpenTelemetry OTLP endpoint for traces.

---

## Summary checklist

| Phase | Action | Priority |
|-------|--------|----------|
| 1 | Gunicorn + static (Whitenoise) | Required before production |
| 1 | `DEBUG=False`, secrets, hosts, CSRF | Required |
| 1 | HTTPS + secure cookies | Required |
| 1 | SMTP email | Required |
| 1 | DB backups | Required |
| 1 | Remove dev auth from repo | Required |
| 2 | Redis persistence, DB pooling | When load grows |
| 2 | S3 media | When uploads matter on Render |
| 3 | Managed HA stack | High traffic |

**Deploy testers now:** [DEPLOY.md](DEPLOY.md) · **Run incidents:** [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)
