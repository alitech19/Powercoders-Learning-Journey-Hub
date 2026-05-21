# Powercoders Learning Journey Hub (powerhub)

Django project with PostgreSQL in Docker.

## Setup guides

| Language | File |
|----------|------|
| English | [SETUP.md](SETUP.md) |

## Setup pipeline (summary)

Full details in [SETUP.md](SETUP.md) 

| Step | Action |
|------|--------|
| 1 | Install Docker & Docker Compose |
| 2 | `git clone <REPO_URL>` |
| 3 | `cd Powercoders-Learning-Journey-Hub` |
| 4 | `cp .env.example .env` |
| 5 | `docker compose up --build` |
| 6 | `docker compose exec web python manage.py createsuperuser` *(new terminal)* |
| 7 | Open http://localhost:8000/accounts/login/ |
