
# PowerHub Workflow Documentation

This document contains Mermaid diagrams for GitHub rendering.

## Setup Pipeline

```mermaid
flowchart LR
A[Install Docker + Docker Compose]
-->B[Clone Repository]
-->C[Create .env File]
-->D[Build Containers]
-->E[Create Superuser]
-->F[Access Application]
```

---

## Detailed Local Setup Flow

```mermaid
flowchart TD

A([Start])
-->B[Install Docker]

B-->C[Install Docker Compose]

C-->D[Verify Installation]

D-->E{Docker Installed?}

E-- No -->B

E-- Yes -->F[Clone Repository]

F-->G[cd Powercoders-Learning-Journey-Hub]

G-->H[Create .env]

H-->I{Edit Environment Variables?}

I-- Yes -->J[Update SECRET_KEY & DB values]

I-- No -->K[docker compose up --build]

J-->K

K-->L[Build Docker Images]

L-->M[Start PostgreSQL Container]

M-->N[Start Django Web Container]

N-->O[Run Automatic Migrations]

O-->P[Create Superuser]

P-->Q[Open localhost:8000]

Q-->R([Application Running])
```

---

## Runtime Architecture

```mermaid
flowchart LR

User[Browser]
<-->Web[Django Container]

Web
<-->DB[PostgreSQL Container]

DB
-->Storage[(postgres_data)]
```

---

## Development Lifecycle

```mermaid
flowchart LR

A[Code Changes]
-->B[docker compose up --build]

B-->C[Container Rebuild]

C-->D[Automatic Migrations]

D-->E[View Browser Changes]

E-->A
```

---

## Recovery Workflow

```mermaid
flowchart LR

A[Migration Error]
-->B[docker compose down -v]

B-->C[docker compose up --build]

C-->D[Create Superuser]

D-->E[Application Restored]
```

GitHub automatically renders Mermaid diagrams inside markdown files.
