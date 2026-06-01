# Business apps roadmap (integration branch)

Greenfield port from `origin/Ali` and `origin/django-test`. Apps are added **one at a time** in **customer priority order** — the same order drives the **main navigation** (left → right).

## Hub vs dashboard

| Phase | URL `/` | Role |
|-------|---------|------|
| **Done** | `dashboard` | Role-based home at `/`; logo links here (not duplicated in nav) |

Nav reads from `config/nav.py`. Per-page **ⓘ** (top-right) opens contextual help (`info` app). `/home/` redirects to dashboard.

## Integration order (customer priority)

Build sequence **2 → 9**, then **dashboard (1)**. Status and names may change during port.

| Build # | App (working name) | Nav label | Source | Status |
|---------|-------------------|-----------|--------|--------|
| 2 | `workflows` | Workflows | Ali | Done |
| 3 | `goals` | Goals | Ali | Done |
| 4 | `tasks` | Tasks | django-test models + Ali UI + enrollment | Done |
| 5 | `reflections` | Reflections | Ali UI + django-test wellbeing dims (embedded) | Done |
| 6 | `journal` | Journal | Ali | Done |
| 7 | `habits` | Habits | django-test (`growth`) | Done |
| 8 | `group_space` | Group | Group chat + resource posts | Done |
| 9 | `resources` | Resources | Group / personal / thematic tiles; file storage: [RESOURCE_FILE_STORAGE.md](RESOURCE_FILE_STORAGE.md) | Done |
| **1 (last)** | `dashboard` | Dashboard | Ali + integration apps | Done |

**Next app to build:** — (integration apps complete; backports remain)

~~**dashboard**~~ ✓ — role-based home at `/`; aggregates tasks, journal, goals, reflections, habits, workflows, group, resources.

| 10 | `info` | — (ⓘ on pages) | In-app help per app | Done |

## Backport from `origin/Ali` (parallel work during integration)

Cherry-pick or re-port **selected** changes from Ali's branch — **not** a merge of `goals` / `workflows` app code (integration architecture differs). Source: commits on `origin/Ali` since project split (~Phase 14–19 + latest refactor).

| # | Area | What to integrate | Source (Ali) | Status |
|---|------|-------------------|--------------|--------|
| B1 | **CI / infra** | GitHub Actions pipeline (PostgreSQL 17 + Redis, migrate + test) | `.github/workflows/ci.yml` | Pending |
| B2 | **CI / infra** | Celery worker and beat as separate containers | `docker-compose.yml` | Pending |
| B3 | **CI / infra** | Guard dev superuser behind `CREATE_DEV_SUPERUSER=true` | `docker-compose.yml`, `.env.example` | Pending |
| B4 | **accounts** | Role decorators (`admin_required`, `teacher_or_admin_required`, `student_required`) | `accounts/decorators.py` | Pending |
| B5 | **accounts** | GDPR self-service account deletion | `accounts/views.py`, templates | Pending |
| B6 | **accounts** | User management UI (list, create, CSV import, deactivate) | `accounts/views.py`, templates | Pending |
| B7 | **accounts** | Student detail + progress overview pages | `accounts/student_detail`, `student_progress` | Pending |
| B8 | **accounts** | In-app notification centre + email preferences | Phase 16 (US-59) | Pending |
| B9 | **notifications** | Slack webhooks (feedback, new users, missing reflections) | Phase 18 (US-65) — wire to `feedback` app, not `GoalComment` | Pending |
| B10 | **feedback / goals** | Email on new feedback | `accounts/emails.py` — target `GoalEnrollment` via generic feedback | Pending |
| B11 | **tests** | Automated test suite pattern (127 tests on Ali) | `*/tests.py` — **rewrite** for integration models, not copy | Pending |
| B12 | **docs** | Incident response runbook + scaling roadmap | `docs/INCIDENT_RESPONSE.md`, `docs/SCALING_ROADMAP.md` | Pending |
| B13 | **group_space** | File uploads on posts (local `media/`) | [RESOURCE_FILE_STORAGE.md](RESOURCE_FILE_STORAGE.md) — Option 1 | Done |
| B14 | **cohorts / accounts** | Bulk assign students to group (admin UI) | Phase 19 (US-39) | Pending |
| B15 | ~~**tasks** Cohort default tasks~~ | — | **Won't do** — teachers assign; enroll on existing task instead |

**Do not backport as-is:** Ali `goals/` and `workflows/` models/views (1 goal per student, goal-level feedback, no shared/private workflow modes). Integration branch is ahead on those; take ideas and tests only after adapting.

### Not in main nav (by design)

- **`feedback`** — generic staff feedback (admin only); wired per app via registry
- **`cohorts`** — admin only (done)
- **`accounts`** — profile, onboarding (done); user mgmt UI later
- **`api`** — health/scaffold when needed
- **`info`** — contextual help (ⓘ top-right); one markdown doc per app with anchors; not in main nav
- **`dashboard`** — landing at `/`; logo target

## Per-app checklist (each PR)

1. Create `backend/<app>/` (models, views, urls, admin if needed)
2. Templates under `frontend/templates/<app>/`
3. Set `enabled=True` on the matching row(s) in `config/nav.py`
4. Migrations + seed touch-ups if dev users need sample data
5. Mark **Done** in the table above

## Rename / split policy

- App package names may differ from nav labels (e.g. nav label "Tasks" → app `tasks`)
- **Reflections** — includes embedded wellbeing check-in; no separate `wellbeing` app
- **Group Space** — single chat lane; any group member can post; achievement snapshots chat-only (not Resources)
- **Resources** — separate app; personal / group / thematic link containers — storage: [RESOURCE_FILE_STORAGE.md](RESOURCE_FILE_STORAGE.md)
- Monolithic django-test `growth` is **not** ported as-is; split per rows above

## Reference

- Auth complete: [AUTH_ROADMAP.md](AUTH_ROADMAP.md)
- Prod dev removal: [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)
