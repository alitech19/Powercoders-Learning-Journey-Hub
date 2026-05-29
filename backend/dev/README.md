# Development seed data

This folder contains **local development only** test users and cohorts.

## Before production deploy — remove from codebase

**Delete this entire dev-user mechanism from the repository before go-live.**  
Do not only set `ENABLE_DEV_SEED=false` — remove the code, templates, commands, and this folder.

Full checklist: [docs/PRODUCTION_CHECKLIST.md](../../docs/PRODUCTION_CHECKLIST.md)

Summary:

1. Delete `backend/dev/` (this folder)
2. Delete dev seed commands, `dev_seed.py`, quick-login views/URLs/templates
3. Remove `ENABLE_DEV_SEED` / `create_dev_superuser` / `seed_dev_data` from settings and `docker-compose.yml`
4. Create the real production admin with `python manage.py createsuperuser`

## Files (development only)

| File | Purpose |
|------|---------|
| `seed.yaml` | Cohorts, groups, students, teachers (unique emails/passwords) |

Super admin for local Docker is **not** in this file — it comes from `DJANGO_SUPERUSER_*` in `.env` via `create_dev_superuser` (also removed before production).
