# Google Drive setup

Operational guide for PowerHUB file storage (hybrid: staff → org Shared drive, students → My Drive).

Related: in-app **Administration → File storage** (ⓘ help) · `/info/google_drive/`

---

## Overview

| Role | Storage | Auth |
|------|---------|------|
| Teacher / admin | Org **Shared drive** (`PowerHUB/Groups/{group}/…`) | Service account (no personal OAuth) |
| Student | Uploader’s **My Drive** (same folder layout) | OAuth (email must match `User.email`) |

**Staff Shared drive** and **student OAuth** are independent. Checking “Enable staff uploads” does **not** enable student Connect on Profile.

Credentials are stored **encrypted in the database** — rotation does not require redeploy.

---

## MVP: student OAuth only (no Workspace)

Use this to test students with Gmail before IT provisions Workspace and Shared drive.

### A. Google Cloud Console

Console: [https://console.cloud.google.com/](https://console.cloud.google.com/)

#### 1. Project + API

1. **Select a project** → **New project** (e.g. `powerhub-dev`).
2. **APIs & Services → Library** → **Google Drive API** → **Enable**.

#### 2. OAuth consent screen

**APIs & Services → OAuth consent screen**

| Field | Value |
|-------|--------|
| User type | **External** |
| App name | e.g. `PowerHUB Dev` |
| User support email | Your Gmail |
| Developer contact | Your email |

If status is **Testing**, add each student email under **Test users** (must match PowerHUB `User.email`).

**Data access scopes:** add **Google Drive** → `drive.file` (per-file access). Without it, Profile connect fails.

#### 3. OAuth client ID + secret

**APIs & Services → Credentials → Create credentials → OAuth client ID**

| Field | Value |
|-------|--------|
| Application type | **Web application** |
| Name | e.g. `PowerHUB local` |
| Authorized redirect URIs | `http://localhost:8000/accounts/google/callback/` (or your `SITE_URL` + `/accounts/google/callback/`) |

After **Create**, copy:

- **Client ID** — `….apps.googleusercontent.com`
- **Client secret** — shown once; copy immediately

To rotate a lost secret: **Credentials** → client → **Add secret**.

### B. PowerHUB — Administration → File storage

Section **Students (My Drive)**:

1. **Enable student OAuth uploads** ✓
2. **OAuth client ID** — from step A.3
3. **OAuth client secret** — from step A.3
4. **Redirect URI** — must match GCP exactly (use **Suggested** on the page)
5. **Workspace email domain** — leave **empty** (allows Gmail)
6. **Save settings** → **Validate OAuth config**

Ensure `.env`:

```env
SITE_URL=http://localhost:8000
```

### C. Student test

1. **Profile → Connect Google Drive** (Google email = PowerHUB email).
2. Group chat → attach file or **New Google file** → **resource name** → appears in Resources.

Leave **Enable staff uploads** off until Shared drive is ready.

---

## Full setup: Google Workspace + staff Shared drive

When the organisation has **Google Workspace**, IT provisions a Shared drive and a GCP service account. Student OAuth can use the **same GCP project**.

### A. Google Workspace (admin.google.com / Drive)

#### 1. Shared drive

1. **Shared drives → New** — e.g. `PowerHUB Files`.
2. Add **teachers** as **Contributor** (via group recommended, e.g. `teachers@yourdomain.org`).
3. Copy **Shared drive ID** from the browser URL:
   `https://drive.google.com/drive/folders/<ID>`

#### 2. Policies

- **Drive API** allowed for the organisation.
- **Link sharing** / external sharing policy must allow **anyone with the link** (PowerHUB sets this on each upload so students without drive membership can open files).

#### 3. Roles (reference)

| Actor | Shared drive role |
|-------|-------------------|
| Service account (`…@….iam.gserviceaccount.com`) | **Content manager** |
| Teachers | **Contributor** |
| PowerHUB admin (human) | **Content manager** (optional, for manual Drive cleanup) |

### B. Google Cloud — service account

Console: [https://console.cloud.google.com/](https://console.cloud.google.com/)

1. **APIs & Services → Library → Google Drive API → Enable**
2. **IAM & Admin → Service accounts → Create service account**
   - Name: e.g. `powerhub-drive-uploader`
   - No extra project IAM role required if SA is member on the Shared drive
3. **Keys → Add key → JSON** — download once
4. **Drive → Shared drive → Manage members** → add `client_email` from JSON as **Content manager**

### C. PowerHUB — File storage (staff section)

1. **Enable staff uploads to org Shared drive** ✓
2. **Shared drive ID** — from step A.1
3. **Display name** — optional label
4. **Service account JSON** — paste full JSON from step B.3
5. **Save settings**
6. **Test Shared drive connection**
7. **Ensure PowerHUB root folder**

`staff_uploads_enabled` = checkbox + drive ID + SA JSON.

Teachers upload in group chat **without** connecting Google on Profile.

### D. Students on Workspace (same org)

In addition to staff setup, configure **Students (My Drive)**:

| Setting | Workspace org |
|---------|----------------|
| OAuth consent screen | **Internal** (if GCP under same org) |
| **Workspace email domain** | `yourdomain.org` |
| OAuth client + secret | Same as MVP section |

Student Google email must match PowerHUB email.

### Folder layout

```
Org Shared drive (staff)          Student My Drive
└── PowerHUB/                     └── PowerHUB/
    └── Groups/                         └── Groups/
        └── {cohort} — {group}/             └── {cohort} — {group}/
```

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Student: “not enabled on this server” | **Student OAuth** checkbox + client ID + secret (not staff checkbox alone) |
| `redirect_uri_mismatch` | Redirect URI identical in GCP and File storage; `SITE_URL` correct |
| OAuth blocked / access denied | Student in **Test users** (Testing mode) |
| Drive scope not granted | Consent screen → **drive.file** scope; revoke app at myaccount.google.com/permissions |
| Email mismatch on connect | Google account email = PowerHUB email |
| Staff upload fails | SA on Shared drive as **Content manager**; drive ID; checkbox + JSON saved |
| Test Shared drive fails | SA `client_email` must be member of the **Shared drive**, not only GCP IAM |
| Students cannot open staff links | Workspace policy blocks “anyone with the link” |
| Teacher cannot delete org upload | By design — admin only for Shared drive files |
| Upload stuck “pending” | Celery **worker** + Redis |
| Resource tile missing | Upload `ready`; resource name on post |

---

## Local development

```bash
docker compose up --build
```

Requires **web**, **worker**, **redis**. `web`/`worker`/`beat` run `locked_migrate` on start.

```bash
docker compose exec web python manage.py createsuperuser
```

See [SETUP.md](SETUP.md).

---

## Production checklist

- [ ] `SITE_URL` matches OAuth redirect host (https in prod)
- [ ] Celery worker running
- [ ] Student OAuth end-to-end tested
- [ ] Staff Shared drive + SA when using teacher uploads
- [ ] OAuth consent screen published or test users maintained

See [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).
