<div align="center">

# {POWER.CODERS} Hub

**The Learning Journey Platform for Powercoders Bootcamp Participants**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-223%20passing-22C55E?style=flat-square)](#-testing)
[![License](https://img.shields.io/badge/License-Private-B23149?style=flat-square)](#)

<br/>

> A private Django web application built exclusively for [Powercoders](https://powercoders.org) —
> a coding bootcamp for refugees and people with a migrant background.

<br/>

[Getting Started](#-getting-started) · [Features](#-features) · [Architecture](#-architecture) · [Branches](#-branches) · [Documentation](#-further-reading)

</div>

---

## 📖 Overview

**PowerHUB** is the learning platform on branch **`integration`**: modular Django apps, enrollment-based tasks, Group Space with JSON snapshots, and one permissions layer in `cohorts.permissions`.

Students document their journey; teachers monitor progress and leave feedback; admins manage cohorts and users. Everyone connects through **Group Space** (chat, shares, resources).

### Three roles. One platform.

| Role | Experience |
|---|---|
| 🎓 **Student** | Journal, reflections, goals, tasks, habits, workflows, group chat, resources; welcome onboarding; data export |
| 👩‍🏫 **Teacher** | Group-scoped dashboard, reflection alerts, student progress, feedback, assign goals/tasks/workflows |
| ⚙️ **Admin** | **Administration** menu — users, cohorts, import, audit log, Django admin; full teacher capabilities |

Home at `/` is a **role-based dashboard**. Contextual **ⓘ help** is in the page content (not the global navbar).

---

## ✨ Features

### For Students

| Module | What it does |
|---|---|
| 📓 **Learning Journal** | Daily entries with mood and tags; private or shared with teacher; teacher feedback |
| 🎯 **Goals** | Hard / soft / language goals with milestones; staff-assigned goals |
| ✅ **Tasks** | Personal and teacher-assigned tasks (`Task` + `TaskEnrollment`) — not a separate tracker app |
| 🔄 **Reflections** | Structured weekly check-ins with wellbeing fields |
| 💪 **Habits** | Weekly targets, streaks; share snapshots to group chat |
| 👥 **Group Space** | Group feed — posts, comments, pins, files, **share panel** (goals, tasks, journal, habits) |
| 📁 **Resources** | Group resource board; items from chat posts labelled as resources |
| 🔀 **Workflows** | Teacher-defined step paths |

### For Teachers & Admins

| Feature | Description |
|---|---|
| 📊 **Dashboard** | Student onboarding checklist; teacher management cards; missing-reflection context |
| 💬 **Structured Feedback** | On journal, reflections, goals, habits, tasks (generic `FeedbackEntry`) |
| 📋 **Student Progress** | `/accounts/users/` progress views (admin / teacher) |
| 🗂️ **Cohort Management** | Django admin + management UI — cohorts, groups, `GroupTeacher` |
| 📥 **Bulk User Import** | CSV import for students and teachers |
| 🔍 **Audit Log** | Security-sensitive actions |
| 📈 **Platform context** | Admin dashboard and analytics cards |

### Platform-wide

| Capability | Details |
|---|---|
| 🔐 **Two-Factor Auth** | TOTP for staff (django-two-factor-auth) |
| 🛡️ **Security** | django-axes, CSP, Redis sessions, secure cookies when `DEBUG=False` |
| 🔔 **Notifications** | In-app centre with unread badge; optional email |
| 💬 **Slack** | Optional webhook for key events |
| 📤 **Data Export** | JSON, CSV, Markdown |
| ❌ **Account Deletion** | GDPR erasure flow |
| ♿ **Accessible** | Skip link to `#main-content`, ARIA on nav, keyboard-friendly dropdowns |

**Navbar (English):** Learning ▾ · Wellbeing ▾ · Group Space · Resources · Administration ▾ (admin, right) · notifications · profile.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser Client                       │
│   Tailwind · HTMX · Alpine (CDN on integration branch)  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────┐
│                   Django Application                     │
│  accounts · cohorts · dashboard · tasks · goals · journal │
│  reflections · habits · workflows · group_space · resources │
│  feedback · info                                         │
│                                                          │
│  cohorts.permissions  ←  role and group checks           │
│  config/nav.py        ←  NavGroup + admin menu           │
└──────────────┬───────────────────────┬───────────────────┘
               │                       │
┌──────────────▼──────┐   ┌────────────▼────────────────┐
│  PostgreSQL 17       │   │  Redis · sessions · Celery   │
└─────────────────────┘   └───────────────┬────────────────┘
                                          │
                           ┌──────────────▼────────────────┐
                           │  Celery worker + Beat (DB)    │
                           └─────────────────────────────┘
```

On **`integration`**, CSS/JS load from CDNs for faster template work. Before production, compile Tailwind and self-host assets — [docs/PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md).

### Key design decisions

- **`Group → GroupSpace → Post`** — chat history decoupled from the group entity.
- **Enrollment-based tasks** — per-student progress on shared assignments.
- **Generic feedback** — one `FeedbackEntry` via ContentTypes across apps.
- **`cohorts.permissions`** — single module for `user_is_admin` / `user_is_teacher` / `user_is_student` and group scoping.
- **Celery schedules** — register periodic tasks in Django admin, not hard-coded `CELERY_BEAT_SCHEDULE`.

---

## 🛠️ Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python | 3.12 |
| Framework | Django | 5.x |
| Database | PostgreSQL | 17 |
| Cache & queue | Redis | 7 |
| Tasks | Celery + django-celery-beat | DB scheduler |
| Frontend | Tailwind, HTMX, Alpine | CDN on `integration`; compiled before prod |
| Auth | django-two-factor-auth, django-axes | |
| Production | Gunicorn + Whitenoise | Render `deploy` branch |
| Local | Docker Compose | `runserver` on `integration` |
| CI | GitHub Actions | Per-app tests |

Health: `GET /health/` · `?db=1` on Render to verify DB host.

---

## 📁 Project Structure

```
Powercoders-Learning-Journey-Hub/
├── backend/
│   ├── accounts/          # Users, 2FA, notifications, management UI, welcome
│   ├── cohorts/           # Cohort, group, permissions
│   ├── config/            # settings, URLs, Celery, nav.py
│   ├── dashboard/
│   ├── tasks/ goals/ journal/ reflections/ habits/
│   ├── workflows/ group_space/ resources/
│   ├── feedback/ info/
│   ├── test_utils/        # Test factories
│   ├── tests/             # Cross-app tests
│   └── manage.py
├── frontend/
│   ├── templates/         # base.html, apps, includes
│   └── static/            # favicon, avatars (app.css after prod bundle)
├── docs/
│   ├── SETUP.md           # Local Docker
│   ├── TESTING.md         # Host + Docker test workflows
│   ├── DEPLOY.md          # Render tester
│   └── …
├── scripts/               # render-web-start.sh, render-beat-start.sh
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 🌿 Branches

| Branch | Purpose |
|---|---|
| **`integration`** | Daily development — [docs/SETUP.md](docs/SETUP.md) |
| **`deploy`** | Render tester — merge from `integration`, [docs/DEPLOY.md](docs/DEPLOY.md) |
| **`main`** | Production target when go-live is ready |

```bash
git checkout integration
# develop, test …
git checkout deploy && git merge integration && git push origin deploy
```

Each Render deploy runs **`migrate` on start** (fresh tester DB; no merge workflow with legacy `main`).

---

## 🚀 Getting Started

> **Full instructions:** [docs/SETUP.md](docs/SETUP.md) · **Render testers:** [docs/DEPLOY.md](docs/DEPLOY.md)

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Compose v2
- Git

### Quick start

```bash
git clone <REPO_URL>
cd Powercoders-Learning-Journey-Hub
git checkout integration
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000/account/login/

| Dev login | How |
|---|---|
| Quick-login panel | `ENABLE_DEV_SEED=true` in `.env` |
| Email + password | Users in `backend/dev/seed.yaml` or `CREATE_DEV_SUPERUSER=true` |

Migrations run automatically on first `docker compose up`.

### Services

| Service | Role | Port |
|---|---|---|
| `web` | Django dev server | `8000` |
| `worker` | Celery worker | — |
| `beat` | Celery Beat | — |
| `db` | PostgreSQL 17 | internal |
| `redis` | Cache + broker | internal |

---

## 🧪 Testing

**223 tests** on `integration`.

```bash
docker compose exec web python manage.py test
```

Host workflow (venv + Postgres in Docker): **[docs/TESTING.md](docs/TESTING.md)**

```bash
# Faster settings (no Redis on host)
export DJANGO_SETTINGS_MODULE=config.settings_test
export POSTGRES_HOST=localhost
cd backend && python manage.py test
```

Factories: `backend/test_utils/` (`make_student`, `make_cohort`, …).

---

## 🤝 Contributing

### Branch strategy

```
main          ← production (when ready)
integration   ← daily development
deploy        ← Render tester (merge from integration)
```

Develop on **`integration`**. Merge to **`deploy`** for shared QA. Do not treat `main` as the active dev line.

### Code style

- **Permissions:** `cohorts.permissions` and per-app `permissions.py`
- **Templates:** Tailwind utilities; HTMX partials; Alpine for nav
- **Tests:** `test_utils` factories; run full suite before merging to `deploy`

CI: `.github/workflows/ci.yml` — migrate, migration check, per-app `manage.py test`.

---

## 📚 Further reading

| Document | Description |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | Local Docker, env, Celery, cohorts |
| [docs/TESTING.md](docs/TESTING.md) | Linux / Windows / Docker test commands |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Render web, worker, beat |
| [docs/PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md) | Go-live (CDN → compiled assets, remove dev auth) |
| [docs/INCIDENT_RESPONSE.md](docs/INCIDENT_RESPONSE.md) | Incidents |
| [docs/USABILITY_TESTING.md](docs/USABILITY_TESTING.md) | Usability plan |
| [.env.render-test.example](.env.render-test.example) | Render tester env template |

---

## 📄 License

Private — all rights reserved. Built for [Powercoders](https://powercoders.org).

---

<div align="center">

Built for **Powercoders** — a coding bootcamp for refugees and people with a migrant background.

**{POWER.CODERS}**

</div>
