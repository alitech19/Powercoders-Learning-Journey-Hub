# Production deploy checklist

Use this before every production (or public staging) deployment.

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

## Optional (when implemented later)

- [ ] 2FA enabled and enforced for staff
- [ ] `django-axes` / rate limiting active
- [ ] HTTPS only, secure cookies

## After deploy

- [ ] Create production admin manually with a strong password
- [ ] Confirm no test users from `seed.yaml` were ever loaded on this environment

---

**Why:** Dev seed stores weak passwords in git and provides one-click login without a password. This is for local QA only — **remove it from the codebase before production**, do not rely on env flags alone.
