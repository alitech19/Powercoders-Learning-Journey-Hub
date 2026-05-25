# Powerhub — local setup (Docker)

Run the steps below **in order**. Copy one command block at a time.

---

## Setup pipeline

### Step 1 — Install prerequisites

Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/).

Verify:

```bash
docker --version
```

```bash
docker compose version
```

---

### Step 2 — Clone the repository

```bash
git clone <REPO_URL>
```

---

### Step 3 — Enter the project folder

```bash
cd Powercoders-Learning-Journey-Hub
```

All following commands run from this directory.

---

### Step 4 — Create environment file

```bash
cp .env.example .env
```

Edit `.env`:

- Set `DEBUG=True`
- Set `ENABLE_DEV_LOGIN=True`

`.env` is gitignored and is not committed.

---

### Step 5 — Build and start containers

Foreground (logs in this terminal):

```bash
docker compose up --build
```

Wait until you see `Starting development server at http://0.0.0.0:8000/`.  
Migrations run automatically on startup.  
Development users are created automatically when `ENABLE_DEV_LOGIN=True`.

**Alternative — background mode** (skip if you use foreground):

```bash
docker compose up --build -d
```

---

### Step 6 — Log in

Open in the browser:

| What                  | URL                                   |
|-----------------------|---------------------------------------|
| Home (requires login) | http://localhost:8000/                |
| Login                 | http://localhost:8000/accounts/login/ |
| Admin                 | http://localhost:8000/admin/          |

The login page shows **quick login buttons**:

- **Login as Student** — logs in as student@example.com
- **Login as Teacher** — logs in as teacher@example.com
- **Login as Admin** — logs in as admin@example.com

No manual user creation needed.

---

## Development users

Created automatically by `python manage.py create_dev_users` (runs on Docker startup).

| Role    | Email               | Password      |
|---------|---------------------|---------------|
| Student | student@example.com | student12345  |
| Teacher | teacher@example.com | teacher12345  |
| Admin   | admin@example.com   | admin12345    |

Also creates:
- Demo Cohort (active)
- Demo Group (in Demo Cohort)
- GroupTeacher relation (Teacher → Demo Group)

Credentials come from `DEV_*` variables in `.env`.

---

## After setup — common commands

Use when needed (not part of the first-time pipeline).

### Check container status

```bash
docker compose ps
```

### View logs

```bash
docker compose logs -f web
```

### Run migrations manually

```bash
docker compose exec web python manage.py migrate
```

### Recreate dev users manually

```bash
docker compose exec web python manage.py create_dev_users
```

### Shell inside the web container

```bash
docker compose exec web sh
```

### Stop containers

```bash
docker compose down
```

---

## Reset database (only if migrations break)

**Deletes all database data.** Run in order:

```bash
docker compose down -v
```

```bash
docker compose up --build
```

Dev users are recreated automatically on startup.

---

## Environment variables

`.env.example` is split into two sections:

**Required (core):**
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`

**Development (quick login and demo data):**
- `ENABLE_DEV_LOGIN` — enables quick login buttons (requires `DEBUG=True`)
- `DEV_STUDENT_*`, `DEV_TEACHER_*`, `DEV_ADMIN_*` — credentials for dev users
- `DEV_COHORT_NAME`, `DEV_GROUP_NAME` — demo data names

Missing `DEV_*` variables are treated as disabled. The app does not crash if they are absent.

---

## Production deployment

- Set `DEBUG=False`
- Do **not** set `ENABLE_DEV_LOGIN` or `DEV_*` variables
- Quick login buttons are hidden; quick login URLs return 403

---

## Services

| Service | Description                           |
|---------|---------------------------------------|
| `web`   | Django (Python 3.12), port `8000`     |
| `db`    | PostgreSQL 16, volume `postgres_data` |

---

## Troubleshooting

| Problem                  | What to do                                                                         |
|--------------------------|------------------------------------------------------------------------------------|
| Port 8000 in use         | In `docker-compose.yml` use `"8080:8000"`, open http://localhost:8080/             |
| Missing `.env`           | Repeat Step 4: `cp .env.example .env`                                              |
| DB connection fails      | `POSTGRES_HOST=db` in `.env`; run `docker compose ps` — wait until `db` is healthy |
| Code changes not visible | `docker compose up --build`                                                        |
| Quick login not showing  | Check `DEBUG=True` and `ENABLE_DEV_LOGIN=True` in `.env`                           |
