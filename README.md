# Powercoders Learning Journey Hub

A web platform for Powercoders bootcamp participants to track their learning journey — journal entries, weekly reflections, goals, tasks, habits, group collaboration, teacher workflows, and resources — all in one place.

Codename: **PowerHUB**.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [User Roles](#user-roles)
- [Branches](#branches)
- [Documentation](#documentation)
- [Contributing](#contributing)

---

## Overview

The Learning Journey Hub is a private Django application for the Powercoders coding bootcamp. Three roles, each with a tailored experience:

- **Students** — journal, reflections (including wellbeing), personal goals and tasks, habits, group feed, teacher workflows, and resource board; export their data; manage notification preferences
- **Teachers** — dashboard with cohort/group context, students missing weekly reflections, student detail (shared journal, goals, reflections), feedback on entries, goals and tasks for learners, group announcements
- **Admins** — user list, create, CSV import, cohort and group CRUD, student progress, audit-oriented tooling, plus full teacher capabilities

The home page at `/` is a **role-based dashboard**. Contextual **ⓘ help** is available per app from the navbar.

---

## Features

| Area | Capabilities |
|------|-------------|
| **Dashboard** | Student, teacher, and admin home — cards for goals, tasks, reflections, management links, and cohort-aware group context |
| **Journal** | Personal entries with mood, tags, visibility (private / shared with teachers), teacher feedback |
| **Reflections** | Weekly and structured reflections; wellbeing embedded in the reflections app |
| **Goals** | Goals with milestones, categories, progress; teachers can set goals for students |
| **Tasks** | Personal and assigned tasks with status workflow (not a separate tracker app) |
| **Habits** | Habit tracking with streaks |
| **Workflows** | Teacher-defined ordered learning paths; students complete steps |
| **Group Space** | Per-group feed — announcements, comments, shared snapshots, file posts |
| **Resources** | Group resource tiles synced from group chat posts labelled **Resource** |
| **Accounts & privacy** | Email login, onboarding (privacy policy, password change, welcome), profile; **Markdown data export**; delete own account |
| **Notifications** | In-app centre with unread badge; optional email for feedback and related events |
| **Integrations** | Welcome email on user create/import; feedback notifications; optional **Slack** webhook for staff digests; **Celery** + **Beat** for scheduled jobs |
| **Admin & cohorts** | In-app user management (`/accounts/users/`), cohorts and groups (`/accounts/cohorts/`), student progress and detail |
| **Security** | Argon2 passwords, **TOTP 2FA** for staff, django-axes lockout, CSP, Redis-backed sessions, JSON request logging |
| **Help** | In-app topics under `backend/info/topics/` (dashboard, accounts, …) |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| Framework | Django 5.x |
| Database | PostgreSQL 17 |
| Cache / sessions | Redis (`django-redis`) |
| Task queue | Celery + `django-celery-beat` |
| Frontend | Tailwind CSS (CDN), HTMX, Alpine.js |
| Auth | `django-two-factor-auth` (TOTP), `django-axes` |
| Containerisation | Docker Compose (local); [Render](docs/DEPLOY.md) (tester deploy) |

Health check: `GET /health/`.

---

## Project Structure

```
Powercoders-Learning-Journey-Hub/
├── backend/                 # Django apps and config
│   ├── accounts/            # Users, 2FA, notifications, GDPR, management UI
│   ├── cohorts/           # Cohort, group, group–teacher models
│   ├── config/              # settings, URLs, Celery, nav registry
│   ├── dashboard/           # Role-based home
│   ├── goals/ journal/ reflections/ tasks/ habits/
│   ├── workflows/ group_space/ resources/
│   ├── feedback/ info/
│   └── manage.py
├── frontend/
│   ├── templates/           # Server-rendered UI + HTMX partials
│   └── static/
├── docs/                    # Setup, testing, deploy, ops (see below)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## User Roles

### Student

- Journal, reflections, goals, tasks, habits, workflows assigned by teachers
- Group feed and resources for their cohort group
- Profile: export data (Markdown), notification settings, delete account

### Teacher

- Everything relevant to their **groups** (via group–teacher links)
- Dashboard alerts for missing weekly reflections
- Student progress and detail; feedback on journal and related items
- Group posts and resource-labelled uploads

### Admin

- User create / import / deactivate; cohort and group management
- Student oversight and Django admin (`/admin/`) for low-level data
- Platform configuration (e.g. periodic Celery tasks in admin)

Roles are set on the user record (`student`, `teacher`, `admin`).

---

## Branches

| Branch | Purpose |
|--------|---------|
| `integration` | **Default for development** — Docker Compose, [docs/SETUP.md](docs/SETUP.md), `.env` |
| `deploy` | **Render tester** — same app code; connect Render to this branch, [docs/DEPLOY.md](docs/DEPLOY.md), `.env.render-test.example` |
| `main` | Production target when go-live is ready |

Workflow: feature work on `integration` → when ready for testers, `git merge integration` into `deploy` and push → Render redeploys. Keep `deploy` in sync with `integration` so both branches share Gunicorn/Whitenoise/`DATABASE_URL` support; only runbooks and env templates differ.

---

## Documentation

Guides live in **`docs/`** (setup, tests, deploy, ops).

| Document | Description |
|----------|-------------|
| [docs/SETUP.md](docs/SETUP.md) | **Local development** — Docker Compose, `.env`, login, Celery, troubleshooting |
| [docs/TESTING.md](docs/TESTING.md) | **Automated tests** — venv, Postgres, coverage, CI |
| [docs/DEPLOY.md](docs/DEPLOY.md) | **Tester deploy on Render** — `deploy` branch, profiles, worker + beat |
| `.env.render-test.example` | Env template for Render tester deploy (`DEBUG=True` + seed) |
| [docs/PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md) | Production go-live (remove dev auth, secrets) |
| [docs/INCIDENT_RESPONSE.md](docs/INCIDENT_RESPONSE.md) | Incident runbook |
| [docs/SCALING_ROADMAP.md](docs/SCALING_ROADMAP.md) | Scaling and architecture phases |
| [docs/USABILITY_TESTING.md](docs/USABILITY_TESTING.md) | Usability test plan (≥5 participants) |
| [docs/RESOURCE_FILE_STORAGE.md](docs/RESOURCE_FILE_STORAGE.md) | Group file storage options |
| [docs/TODO.md](docs/TODO.md) | Beat schedules, Slack follow-ups |

**Quick pointers:** run locally → [docs/SETUP.md](docs/SETUP.md) · run tests → [docs/TESTING.md](docs/TESTING.md) · deploy for testers → [docs/DEPLOY.md](docs/DEPLOY.md)

---

## Contributing

### Workflow

```bash
git checkout integration
git pull origin integration
# make changes, run tests — see docs/TESTING.md
git push origin integration
```

For tester deploy: merge into `deploy` and follow [docs/DEPLOY.md](docs/DEPLOY.md).

### Code style

- Python: PEP 8, match existing app patterns
- Templates: Tailwind utilities; HTMX for partial updates; Alpine.js where needed
- Prefer extending existing services and permissions over new abstractions

### CI

GitHub Actions (`.github/workflows/ci.yml`): migrations check and `manage.py test` per app on push/PR.

---

*Built for [Powercoders](https://powercoders.org) — a coding bootcamp for refugees and people with a migrant background.*
