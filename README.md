<div align="center">

<img src="frontend/static/img/powercoders-wordmark.svg" alt="POWER.CODERS" width="420">

# Learning Journey Hub

**The Learning Journey Platform for Powercoders Bootcamp Participants**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-251%20passing-22C55E?style=flat-square)](#-testing)
[![License](https://img.shields.io/badge/License-Private-B23149?style=flat-square)](#)

<br/>

> A private Django web application built exclusively for [Powercoders](https://powercoders.org) —
> a coding bootcamp for refugees and people with a migrant background in Switzerland.

<br/>

[Getting Started](#-getting-started) · [Features](#-features) · [Architecture](#-architecture) · [Deployment](#-deployment) · [Documentation](#-further-reading)

</div>

---

## 📖 Overview

**PowerHUB** brings together every tool Powercoders students and teachers need into a single, privacy-first platform. It replaces fragmented tooling (Notion, Slack, Google Docs) with one cohesive learning journey application.

Students document their progress, teachers monitor and give feedback, and admins manage the platform lifecycle. Everyone connects through a real-time Group Space with resource sharing and achievement snapshots.

### Three roles. One platform.

| Role | Experience |
|---|---|
| 🎓 **Student** | Journal · Goals · Tasks · Reflections · Habits · Workflows · Group chat · Resources |
| 👩‍🏫 **Teacher** | Dashboard · Reflection alerts · Student progress · Structured feedback · Workflow creation |
| ⚙️ **Admin** | Full platform control — cohorts, users, CSV import, audit log, analytics |

Home at `/` is a **role-based dashboard**. Contextual **ⓘ help** is in the page content (not the global navbar).

---

## ✨ Features

### For Students

| Module | What it does |
|---|---|
| 📓 **Learning Journal** | Daily entries with mood and tags; private or shared with teacher; teacher feedback |
| 🎯 **Goals** | Hard / soft / language goals with milestones; staff-assigned goals |
| ✅ **Tasks** | Personal and teacher-assigned tasks (`Task` + `TaskEnrollment`) with per-student subtask status |
| 🔄 **Reflections** | Structured weekly check-ins with well-being fields |
| 💪 **Habits** | Weekly targets, streaks; share snapshots to group chat |
| 👥 **Group Space** | Group feed — posts, comments, pins, files, **share panel** (goals, tasks, journal, habits) |
| 📁 **Resources** | Group resource board; items from chat posts labelled as resources |
| 🔀 **Workflows** | Teacher-defined step paths |

### For Teachers & Admins

| Feature | Description |
|---|---|
| 📊 **Dashboard** | Onboarding checklist · teacher management cards · missing-reflection context |
| 💬 **Structured Feedback** | On journal, reflections, goals, habits, tasks (generic `FeedbackEntry`) |
| 📋 **Student Progress** | `/accounts/users/` progress views (admin / teacher) |
| 🗂️ **Cohort Management** | Django admin + management UI — cohorts, groups, `GroupTeacher` |
| 📥 **Bulk User Import** | CSV import for students and teachers |
| 🔍 **Audit Log** | Security-sensitive actions |
| 📈 **Platform Analytics** | Dedicated analytics dashboard — weekly engagement charts, reflection submission rate, goal completion doughnut, cohort comparison, at-risk student table (7-day inactivity) |

### Platform-wide

| Capability | Details |
|---|---|
| 🔐 **Two-Factor Auth** | TOTP for staff (django-two-factor-auth) |
| 🛡️ **Security** | django-axes (brute force), CSP, Redis sessions, secure cookies when `DEBUG=False` |
| 🔔 **Notifications** | In-app centre with unread badge; optional email per user |
| 📧 **Email delivery** | SMTP via SendGrid or Postmark; console fallback in dev |
| 🐛 **Error monitoring** | Sentry — real-time production errors with full stack traces |
| 💬 **Slack** | Optional webhook for key events (new users, missing reflections) |
| 📤 **Data Export** | JSON, CSV, Markdown — full data portability |
| ❌ **Account Deletion** | GDPR right-to-erasure flow |
| ♿ **Accessible** | Skip link to `#main-content`, ARIA on nav, keyboard-friendly dropdowns |
| 📱 **Progressive Web App** | Installable on mobile; service worker with offline fallback page; Web App Manifest with 3 icon sizes |
| 🌙 **Dark mode** | System preference auto-detected; user toggle (sun/moon) persisted to `localStorage`; zero flash-of-wrong-theme |

**Navbar (English):** Learning ▾ · Wellbeing ▾ · Group Space · Resources · Administration ▾ (admin, right) · notifications · profile.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser Client                       │
│           Tailwind CSS · HTMX · Alpine.js                │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────┐
│                   Django 5.2 Application                 │
│                                                           │
│  accounts · cohorts · dashboard · tasks · goals · journal│
│  reflections · habits · workflows · group_space          │
│  resources · feedback · info · api                       │
│                                                           │
│  cohorts.permissions  ←  role and group checks           │
│  config/nav.py        ←  NavGroup + admin menu           │
│  feedback.FeedbackEntry (ContentTypes / GenericFK)       │
└──────────────┬───────────────────────┬──────────────────┘
               │                       │
┌──────────────▼──────┐   ┌────────────▼───────────────┐
│  PostgreSQL 17       │   │  Redis 7                    │
│                      │   │  Sessions · Celery broker   │
└─────────────────────┘   └─────────────┬───────────────┘
                                        │
                           ┌────────────▼──────────────┐
                           │  Celery Worker + Beat (DB)  │
                           │  · Email notifications      │
                           │  · Slack alerts             │
                           │  · Weekly reminders         │
                           └───────────────────────────┘
```

### Key design decisions

- **`Group → GroupSpace → Post`** — chat history decoupled from the group entity; flexible for future features.
- **Enrollment-based tasks** — `Task` + `TaskEnrollment` gives per-student progress on shared assignments.
- **Generic feedback** — one `FeedbackEntry` via Django ContentTypes; works for Goals, Tasks, Journal, Reflections, Habits.
- **`cohorts.permissions`** — single module for `user_is_admin`, `user_is_teacher`, `user_is_student`, and `get_teacher_group_ids` group scoping.
- **DB-based Celery schedules** — periodic tasks registered via `django-celery-beat` in Django admin (not hard-coded).
- **JSON snapshots** — Group Space achievement cards store structured `snapshot_meta` (JSON), not raw HTML.

---

## 🛠️ Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python | 3.12 |
| Framework | Django | 5.2 |
| Database | PostgreSQL | 17 |
| Cache & queue | Redis | 7 |
| Tasks | Celery + django-celery-beat | DB scheduler |
| Frontend CSS | Tailwind CSS | Compiled v4 (`frontend/static/css/tailwind.css`, built via `npm run build:css`) — `@custom-variant dark` for class-based dark mode |
| Frontend JS | HTMX · Alpine.js | Self-hosted (`frontend/static/js/`) |
| Charts | Chart.js | v4.4.4, self-hosted — analytics dashboard |
| PWA | Web App Manifest + Service Worker | Network-first nav, cache-first static assets, offline fallback |
| Auth | django-two-factor-auth · django-axes | TOTP 2FA + brute-force protection |
| CSP | django-csp | Content Security Policy |
| Email | Django SMTP backend | SendGrid / Postmark in production |
| Error monitoring | Sentry (sentry-sdk) | Enabled via `SENTRY_DSN` env var |
| Production server | Gunicorn + WhiteNoise | Native Python runtime on Render |
| Local development | Docker Compose | Auto-reload `runserver` |
| CI | GitHub Actions | Per-app tests on push |

Health check endpoint: `GET /health/` (add `?db=1` on Render to verify DB connectivity).

---

## 📁 Project Structure

```
Powercoders-Learning-Journey-Hub/
├── backend/
│   ├── accounts/          # Users, 2FA, notifications, management UI, onboarding
│   ├── api/               # REST API (/api/health)
│   ├── cohorts/           # Cohort + Group models, permissions, GroupTeacher
│   ├── config/            # settings.py, urls.py, celery.py, nav.py
│   ├── dashboard/         # Role-based dashboard views
│   ├── feedback/          # Generic FeedbackEntry (ContentTypes)
│   ├── goals/             # Goal + Milestone
│   ├── google_drive/      # Google Drive integration
│   ├── group_space/       # GroupSpace · Post · Comment · snapshots · share panel
│   ├── habits/            # Habit + HabitLog
│   ├── info/              # Contextual help pages
│   ├── journal/           # JournalEntry + comments
│   ├── reflections/       # Weekly reflections
│   ├── resources/         # ResourceContainer + ResourceItem
│   ├── tasks/             # Task · TaskEnrollment · Subtask · TaskUpdate
│   ├── workflows/         # Workflow · WorkflowStep · WorkflowEnrollment
│   ├── test_utils/        # Shared test factories
│   ├── tests/             # Cross-app integration tests
│   └── manage.py
├── frontend/
│   ├── templates/         # base.html, all app templates, partials
│   └── static/            # CSS, JS, images, favicon
├── docs/
│   ├── SETUP.md           # Full local Docker setup
│   ├── TESTING.md         # Test workflows (host + Docker)
│   ├── DEPLOY.md          # Render deployment guide
│   ├── PRODUCTION_CHECKLIST.md
│   ├── INCIDENT_RESPONSE.md
│   ├── SCALING_ROADMAP.md
│   ├── USABILITY_TESTING.md
│   └── plans/             # Feature plans
├── scripts/               # render-web-start.sh, render-beat-start.sh
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── runtime.txt            # Python version pin for Render Native
└── .env.example
```

---

## 🚀 Getting Started

> **Full instructions:** [docs/SETUP.md](docs/SETUP.md)
> **Deploying to Render:** [docs/DEPLOY.md](docs/DEPLOY.md)

### Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/) (includes Compose v2)
- Git

### Quick start

```bash
# 1. Clone the repository
git clone https://github.com/alitech19/Powercoders-Learning-Journey-Hub.git
cd Powercoders-Learning-Journey-Hub

# 2. Copy environment template (defaults work out of the box)
cp .env.example .env

# 3. Build and start all services
docker compose up --build

# 4. Open the app
# http://localhost:8000/account/login/
```

Create your first admin, then log in with email + password (you set up 2FA on first login):

```bash
docker compose exec web python manage.py createsuperuser
```

Add further users from **Administration → Users** (or CSV import) — each gets a temporary password and is forced to change it on first login.

> Migrations run **automatically** on container startup. First build takes ~2 minutes.

### Services

| Service | Role | Port |
|---|---|---|
| `web` | Django dev server | `8000` |
| `worker` | Celery task processor | — |
| `beat` | Celery Beat scheduler | — |
| `db` | PostgreSQL 17 | `5432` (mapped to host) |
| `redis` | Cache + message broker | internal |

---

## 🧪 Testing

**251 tests** pass on main.

### Run all tests (Docker)

```bash
docker compose exec web python manage.py test
```

### Run on the host (faster — no Redis needed)

```bash
export DJANGO_SETTINGS_MODULE=config.settings_test
export POSTGRES_HOST=localhost
cd backend && python manage.py test
```

See **[docs/TESTING.md](docs/TESTING.md)** for full host workflow.

### Test factories

The `backend/test_utils/` package provides factory helpers:

```python
from test_utils.users import make_student, make_teacher, make_admin
from test_utils.cohorts import make_cohort, make_group, assign_teacher
from test_utils.goals import make_student_goal
from test_utils.tasks import make_personal_task
# + journal, habits, reflections, resources, group_space, workflows
```

---

## 🚀 Deployment

PowerHUB deploys to [Render](https://render.com) using:

| Service | Type |
|---|---|
| `powerhub-web` | Web Service (Native Python) |
| `powerhub-worker` | Background Worker (Celery) |
| `powerhub-beat` | Background Worker (Celery Beat) |
| `powerhub-db` | PostgreSQL 17 |
| `powerhub-redis` | Key Value (Redis) |

### Start commands

| Service | Command |
|---|---|
| Web | `chmod +x scripts/render-web-start.sh && ./scripts/render-web-start.sh` |
| Worker | `cd backend && celery -A config worker --loglevel=info --concurrency=1` |
| Beat | `chmod +x scripts/render-beat-start.sh && ./scripts/render-beat-start.sh` |

**Full guide:** [docs/DEPLOY.md](docs/DEPLOY.md) · **Pre-launch checklist:** [docs/PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md)

---

## 🔒 Security

| Mechanism | Implementation |
|---|---|
| Two-Factor Auth | TOTP via django-two-factor-auth — enforced for Teacher and Admin |
| Brute-force | django-axes — 5 failed attempts → 1-hour lockout |
| Session security | Redis-backed sessions; secure cookies in production |
| Content Security Policy | django-csp restricts inline scripts and external origins |
| HTTPS enforcement | Auto-enabled when `DEBUG=False` (HSTS + SSL redirect) |
| Audit Logging | All logins, role changes, and sensitive actions logged |
| GDPR Compliance | Data export (JSON/CSV/Markdown) + account deletion |

---

## 🤝 Contributing

### Branch strategy

```
main              ← source of truth
└── feat/your-feature   ← your feature branch
```

Open a pull request from your feature branch into `main`.

### Code conventions

| Concern | Where it lives |
|---|---|
| Access control | `<app>/permissions.py` — pure functions |
| Business logic | `<app>/services.py` — no HTTP context |
| HTTP handling | `<app>/views.py` — calls permissions + services |
| Form validation | `<app>/forms.py` |
| URL patterns | `<app>/urls.py` with `app_name` namespace |
| Templates | Tailwind utility classes; HTMX partials; Alpine for state |
| Tests | `backend/test_utils/` factories — never raw DB setup |

### Before pushing

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py test
```

CI runs: migration check, system check, full test suite per app.
Configuration: `.github/workflows/ci.yml`.

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| `TemplateDoesNotExist` | Run `docker compose down && docker compose up --build` |
| Port 8000 in use | Change `'8000:8000'` to `'8080:8000'` in `docker-compose.yml` |
| Missing `.env` | Run `cp .env.example .env` |
| Database connection refused | Verify `POSTGRES_HOST=db` in `.env`; check `docker compose ps` |
| Static files not loading | Run `docker compose exec web python manage.py collectstatic --noinput` |
| 2FA device lost | `/admin/` → OTP Devices → delete the user's device |
| Account locked (axes) | `/admin/` → Access Attempts → clear the entry |
| Migration conflict | `docker compose down -v && docker compose up --build` (resets DB) |

---

## 📚 Further reading

| Document | Description |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | Full local Docker setup with env, Celery, cohorts |
| [docs/TESTING.md](docs/TESTING.md) | Linux / Windows / Docker test commands |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Step-by-step Render web, worker, beat setup |
| [docs/PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md) | Pre-launch checklist |
| [docs/INCIDENT_RESPONSE.md](docs/INCIDENT_RESPONSE.md) | Runbook for platform incidents |
| [docs/SCALING_ROADMAP.md](docs/SCALING_ROADMAP.md) | Plan for scaling beyond Render |
| [docs/USABILITY_TESTING.md](docs/USABILITY_TESTING.md) | Usability test plan |
| **[Project Wiki](https://github.com/alitech19/Powercoders-Learning-Journey-Hub/wiki)** | User guides, architecture, deployment |

---

## 📄 License

Private — all rights reserved. Built for [Powercoders](https://powercoders.org).

---

<div align="center">

Built with ❤️ for **Powercoders** —
a coding bootcamp for **refugees and people with a migrant background** in Switzerland.

**{POWER.CODERS}**

</div>
