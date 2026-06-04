# Production deploy checklist

Use this before every **production** deployment.

For a **tester-only** host on Render (`deploy` branch), see [DEPLOY.md](DEPLOY.md). Local dev: [SETUP.md](SETUP.md). Dev seed may stay in the repo until a production release, but do not expose weak dev passwords on a public URL.

## Pre-production bundle (deferred on `integration`)

On the **`integration`** branch we **intentionally keep** the CDN-based frontend (Tailwind compiler in the browser, HTMX/Alpine from CDNs) while merging features from `main`. That is faster for day-to-day template work and does not block feature integration.

**Do not go live with CDN Tailwind.** Complete this block in the **same pre-release pass** as [dev users removal](#dev-users--remove-from-the-codebase) (one PR or release branch, e.g. `deploy` → production).

### Frontend: compiled CSS and self-hosted JS (from `main` / phase “perf”)

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

**Dev workflow until then:** CDN remains on `integration`; acceptable for local QA. Staging on Render may be slower or CDN-dependent — plan the perf block before exposing testers to a “production-like” URL.

### Already done on `integration` (do not repeat)

- [x] Production security when `DEBUG=False`: HTTPS redirect, HSTS, secure cookies, `SECRET_KEY` guard, `SECURE_REFERRER_POLICY` (see `.env.example` production comments)
- [x] Celery beat: `migrate` before beat in `docker-compose.yml` and `scripts/render-beat-start.sh`
- [x] Gunicorn + WhiteNoise in `requirements.txt` (Render uses Gunicorn; local compose may still use `runserver`)

### Optional in same pre-prod pass

- [ ] Error pages: `frontend/templates/404.html`, `403.html`, `500.html`
- [ ] a11y/i18n from `main`: skip link, landmarks, `LocaleMiddleware`, `/i18n/` (if required for launch)

---

## Dev users — remove from the codebase

**Do not ship dev-only auth to production.** Disabling `ENABLE_DEV_SEED` is not enough for go-live — **delete the dev-user mechanism from the repository** before the production deploy (or in a dedicated pre-release commit/PR).

### Remove these files and folders

- [ ] `backend/dev/` (entire folder — `seed.yaml`, README)
- [ ] `backend/accounts/dev_seed.py`
- [ ] `backend/accounts/management/commands/seed_dev_data.py`
- [ ] `backend/accounts/management/commands/create_dev_superuser.py`
- [ ] `frontend/templates/registration/_dev_login_panel.html`

### Remove or revert code references

- [ ] `accounts/views.py` — `dev_quick_login` view
- [ ] `accounts/urls.py` — `dev-login/<email>/` route
- [ ] `accounts/context_processors.py` — `dev_login_panel` (delete file if nothing else remains)
- [ ] `config/settings.py` — `ENABLE_DEV_SEED`, `DEV_SEED_FILE`, `DEV_SUPERUSER_EMAIL`, and `accounts.context_processors.dev_login_panel` from `TEMPLATES`
- [ ] `frontend/templates/two_factor/core/login.html` — dev quick-login section
- [ ] `docker-compose.yml` — `create_dev_superuser` and `seed_dev_data` from the web `command`
- [ ] `.env.example` — `ENABLE_DEV_SEED` and `DJANGO_SUPERUSER_*` blocks
- [ ] `requirements.txt` — `PyYAML` if no longer used elsewhere

### Verify after removal

- [ ] `DEBUG=False` in production `.env`
- [ ] Production start command runs only: `migrate`, `collectstatic`, app server (no seed commands)
- [ ] `/account/login/` — normal email/password form only (no dev panel include)
- [ ] No `dev-login` URL in the project (`grep -r dev.login` / search for `dev_quick_login`)
- [ ] Create production admin manually: `python manage.py createsuperuser`

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

---

**Why:** Dev seed stores weak passwords in git and provides one-click login without a password. This is for local QA only — **remove it from the codebase before production**, do not rely on env flags alone.
