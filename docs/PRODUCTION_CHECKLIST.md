# Production deploy checklist

Use this before every **production** deployment.

For a **tester-only** host on Render (`deploy` branch), see [DEPLOY.md](DEPLOY.md). Local dev: [SETUP.md](SETUP.md). Dev seed may stay in the repo until a production release, but do not expose weak dev passwords on a public URL.

## Pre-production bundle (deferred on `main`)

On **`main`** we **intentionally keep** the CDN-based frontend (Tailwind compiler in the browser, HTMX/Alpine from CDNs) for now. That is faster for day-to-day template work while features land via PRs into `main`.

**Do not go live with CDN Tailwind.** Complete this block in the **same pre-release pass** as [dev users removal](#dev-users--remove-from-the-codebase) (one PR or release branch before production).

### Frontend: compiled CSS and self-hosted JS (pre-release “perf” pass)

- [ ] Add `frontend/package.json`, `frontend/src/input.css` (Tailwind v4 with `@source` on templates)
- [ ] Run `cd frontend && npm install && npm run build` → commit `frontend/static/css/app.css`
- [ ] Add `frontend/templates/_head_assets.html`; switch `base.html`, `base_minimal.html`, 2FA/lockout, privacy pages to `{% static %}` — **remove** `cdn.tailwindcss.com`, jsdelivr, unpkg
- [ ] Vendor `frontend/static/js/htmx.min.js` and `alpine.min.js` (self-hosted)
- [ ] Tighten CSP in `config/settings.py`: no `cdn.tailwindcss.com` in `CSP_SCRIPT_SRC` (add `'unsafe-eval'` only if Alpine requires it)
- [ ] Multi-stage `Dockerfile`: Node stage runs `npm run build` before Python image
- [ ] CI / Render build: `npm run build` then `collectstatic` (see [DEPLOY.md](DEPLOY.md))
- [ ] Document in [SETUP.md](SETUP.md): after template/CSS class changes run `npm run build` or `npm run watch` — `docker compose up` does **not** rebuild Tailwind; `collectstatic` only copies existing files

**Verify**

- [ ] Login (and one app page): Network tab shows **no** requests to `cdn.tailwindcss.com`, `cdn.jsdelivr.net`, `unpkg.com`
- [ ] Styles and HTMX/Alpine still work (forms, group chat, Alpine nav)
- [ ] `manage.py test` passes after the switch

**Dev workflow until then:** CDN remains on `main`; acceptable for local QA. Staging on Render (`deploy`) may be slower or CDN-dependent — plan the perf block before exposing testers to a “production-like” URL.

### Already done on `main` (do not repeat)

- [x] Production security when `DEBUG=False`: HTTPS redirect, HSTS, secure cookies, `SECRET_KEY` guard, `SECURE_REFERRER_POLICY` (see `.env.example` production comments)
- [x] Celery beat: `locked_migrate` before beat in `docker-compose.yml` and `scripts/render-beat-start.sh`
- [x] Gunicorn + WhiteNoise in `requirements.txt` (Render uses Gunicorn; local compose may still use `runserver`)

### Optional in same pre-prod pass

- [ ] Error pages: `frontend/templates/404.html`, `403.html`, `500.html`
- [ ] a11y/i18n from `main`: skip link, landmarks, `LocaleMiddleware`, `/i18n/` (if required for launch)

---

## Dev users — remove from the codebase

> **✅ Completed.** The dev-user mechanism has been deleted from the repository, not just disabled:
> `backend/dev/`, `accounts/dev_seed.py`, the `seed_dev_data` and `create_dev_superuser` management commands, `_dev_login_panel.html`, the `dev_quick_login` view + `dev-login/` route, the `dev_login_panel` context processor, the 2FA dev-bypass in `middleware.py`, the dev-seed settings (`ENABLE_DEV_SEED` / `DEV_SEED_FILE` / `DEV_SUPERUSER_EMAIL`), the login-page panel, the Docker/Render seed commands, the `ENABLE_DEV_SEED` / `DJANGO_SUPERUSER_*` env blocks, and `PyYAML` (no longer used).
>
> Verified: `python manage.py check` clean; full test suite (251 tests) passes; `/account/login/` renders the email/password form only (no dev panel); no `dev_quick_login` reference remains.

Still required at deploy time:

- [ ] `DEBUG=False` in production env, with a strong `SECRET_KEY`
- [ ] Create the production admin manually: `python manage.py createsuperuser`

## Secrets & infrastructure

- [ ] `SECRET_KEY` is a new random value (not the dev default)
- [ ] No dev credentials (`@dev.powerhub.local`, weak seed passwords) in production database
- [ ] `.env` is not committed to git
- [ ] Database and Redis are not exposed publicly

## Security (verify on staging with `DEBUG=False`)

- [ ] `python manage.py check --deploy` reports **0 issues** (use a strong random `SECRET_KEY`, set `CSRF_TRUSTED_ORIGINS`)
- [ ] 2FA enabled and enforced for staff (`Require2FAMiddleware`)
- [ ] `django-axes` / rate limiting active
- [ ] HTTPS only, secure cookies (auto when `DEBUG=False` + proxy header on Render)

## After deploy

- [ ] Create production admin manually with a strong password
- [ ] Confirm no test users from `seed.yaml` were ever loaded on this environment
- [ ] Open **Administration → Notifications** — enable reflection digest and deadline reminders (Beat tasks created automatically on save)
- [ ] Open **Administration → Slack integration** — configure OAuth, staff webhook, and/or chat sync if using Slack (no `.env` changes needed; credentials stored encrypted in DB)
- [ ] Verify `SITE_URL` matches the public HTTPS URL exactly (required for Slack OAuth redirect and Events API callbacks)

---

**Why:** Dev seed stores weak passwords in git and provides one-click login without a password. This is for local QA only — **remove it from the codebase before production**, do not rely on env flags alone.
