# Testing

PostgreSQL + `config.settings_test` (no Redis on host). Local app setup: [SETUP.md](SETUP.md).


Always use the project **venv** (`source .venv/bin/activate`) — system `python` usually has no Django or `coverage`.

---

## Linux / macOS

### One-time setup

From the **repository root** (folder with `docker-compose.yml`):

```bash
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### Run tests

From **repo root**:

```bash
source .venv/bin/activate
docker compose up -d db --wait
cd backend
export DJANGO_SETTINGS_MODULE=config.settings_test
export POSTGRES_HOST=localhost
python manage.py test
cd ..
```

**Cleanup** (repo root):

```bash
docker compose down --remove-orphans
```

One app: `python manage.py test cohorts --verbosity=2`  
Cross-app flows: `python manage.py test tests --verbosity=2`  
Faster re-run (before cleanup): `python manage.py test --keepdb`

### Coverage

Same as tests, but from `backend/` with venv active (`pip install -r requirements-dev.txt` once):

```bash
source .venv/bin/activate
docker compose up -d db --wait
cd backend
export DJANGO_SETTINGS_MODULE=config.settings_test
export POSTGRES_HOST=localhost
python -m coverage run --source='.' manage.py test
python -m coverage report
cd ..
```

**Cleanup** (repo root):

```bash
docker compose down --remove-orphans
```


### Tests inside Docker

```bash
docker compose up -d db redis --wait
docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.settings_test web python manage.py test
```

**Cleanup:**

```bash
docker compose down --remove-orphans
```

---

## Windows (PowerShell)

### One-time setup

```powershell
cd <path-to-repo>
Copy-Item .env.example .env
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
```

### Run tests

```powershell
.\.venv\Scripts\Activate.ps1
docker compose up -d db --wait
cd backend
$env:DJANGO_SETTINGS_MODULE = "config.settings_test"
$env:POSTGRES_HOST = "localhost"
python manage.py test
cd ..
```

**Cleanup:**

```powershell
docker compose down --remove-orphans
```

### Coverage

```powershell
.\.venv\Scripts\Activate.ps1
docker compose up -d db --wait
cd backend
$env:DJANGO_SETTINGS_MODULE = "config.settings_test"
$env:POSTGRES_HOST = "localhost"
python -m coverage run --source='.' manage.py test
python -m coverage report
cd ..
```

**Cleanup:**

```powershell
docker compose down --remove-orphans
```

---

## Cleanup (reference)

Run from **repo root** after tests or when you only started `db` for local testing.

**Default — stop and remove containers + network (keeps DB data in volume):**

```bash
docker compose down --remove-orphans
```

**Postgres only** (if you used `docker compose up -d db` and want containers gone):

```bash
docker compose stop db
docker compose rm -f db
```

**Fresh database** (deletes `postgres_data` volume):

```bash
docker compose down -v --remove-orphans
```

| Command | Effect |
|--------|--------|
| `docker compose down --remove-orphans` | Remove test/dev containers and network; **keep** Postgres volume |
| `docker compose down -v --remove-orphans` | Same + **wipe** database volume |

Do not run `down` while the full dev stack is running (`docker compose up`) unless you intend to stop everything.

`manage.py test` uses **`test_powerhub`** — dev DB `powerhub` in the volume is not modified by tests.

---

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| `No module named coverage` | `pip install -r requirements-dev.txt` with venv active |
| `No module named django` | `source .venv/bin/activate` or `.venv/bin/python` |
| `connection refused` on `127.0.0.1:5432` | `docker compose up -d db --wait`; port `5432:5432` must be mapped |
| zsh: `correct 'coverage' to '.coverage'?` | Answer `n`, or use `python -m coverage` |

---

## Intentionally not covered

### Excluded from coverage (`.coveragerc`)

Not targeted by unit tests:

- `*/migrations/*`
- test code: `*/tests/*`, `test_*.py`, `test_utils/*`
- management commands, `dev_seed.py`, `backend/dev/*`
- wiring: `apps.py`, `urls.py`, `admin.py`, `wsgi.py`, `asgi.py`, `config/nav.py`, context processors

### In the repo but still untested (shown in `coverage report`)

- **`views.py`** in most apps — partial coverage in `accounts`, `feedback` only
- **`forms.py`** — exercise via view POST tests when added
- **Integrations**: production Slack webhook / Beat schedule (unit tests in `accounts.tests.test_integrations`)
- Full **2FA login** flows beyond staff TOTP helpers in `test_utils`
