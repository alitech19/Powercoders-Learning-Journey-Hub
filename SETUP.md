# Powerhub — local setup (Docker)

**Also available in Ukrainian:** [SETUP.uk.md](SETUP.uk.md)

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

Optional: edit `.env` (especially `SECRET_KEY` and database password).  
`.env` is gitignored and is not committed.

---

### Step 5 — Build and start containers

Foreground (logs in this terminal):

```bash
docker compose up --build
```

Wait until you see `Starting development server at http://0.0.0.0:8000/`.  
Migrations run automatically on startup.

**Alternative — background mode** (skip if you use foreground):

```bash
docker compose up --build -d
```

---

### Step 6 — Create your first user

Open a **second terminal**, stay in the project folder (`cd` as in Step 3).

```bash
docker compose exec web python manage.py createsuperuser
```

Follow the prompts (username, email, password).

---

### Step 7 — Log in

Open in the browser:

| What | URL |
|------|-----|
| Home (requires login) | http://localhost:8000/ |
| Login | http://localhost:8000/accounts/login/ |
| Admin | http://localhost:8000/admin/ |

Use the credentials from Step 6.

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

### Change a user password

Replace `USERNAME` with the actual username:

```bash
docker compose exec web python manage.py changepassword USERNAME
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

```bash
docker compose exec web python manage.py createsuperuser
```

---

## Services

| Service | Description |
|---------|-------------|
| `web` | Django (Python 3.12), port `8000` |
| `db` | PostgreSQL 16, volume `postgres_data` |

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| Port 8000 in use | In `docker-compose.yml` use `"8080:8000"`, open http://localhost:8080/ |
| Missing `.env` | Repeat Step 4: `cp .env.example .env` |
| DB connection fails | `POSTGRES_HOST=db` in `.env`; run `docker compose ps` — wait until `db` is healthy |
| Code changes not visible | `docker compose up --build` |
