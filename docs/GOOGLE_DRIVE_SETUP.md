# Google Drive setup

Operational guide for PowerHUB file storage (hybrid: staff → org Shared drive, students → My Drive).

Related: [GOOGLE_DRIVE_INTEGRATION_PLAN.md](plans/GOOGLE_DRIVE_INTEGRATION_PLAN.md) · in-app **Administration → File storage** · help topic `/info/google_drive/`

---

## Overview

| Role | Storage | Auth |
|------|---------|------|
| Teacher / admin | Org **Shared drive** (`PowerHUB/Groups/{group}/…`) | Service account (no personal OAuth) |
| Student | Uploader’s **My Drive** (same folder layout) | OAuth (email must match `User.email`) |

All new chat uploads go to Google Drive when configured. Resources tiles use `webViewLink`. Legacy files under `media/group_files/` remain read-only.

**Limits:** 10 MB per chat file; 10 uploads per user per minute; Celery retries failed uploads twice (60s delay). Authors can **Retry upload** in chat while the staged file still exists.

---

## MVP without Google Workspace

Use this path to test with students before IT provisions Workspace.

1. Create a **free GCP project** → enable **Google Drive API**.
2. **OAuth consent screen** → External (testing) → add test users if in testing mode.
3. **Credentials → OAuth Web client** → authorized redirect URI:
   - Local: `http://localhost:8000/accounts/google/callback/`
   - Staging/prod: `https://<SITE_URL>/accounts/google/callback/`
4. **Administration → File storage:**
   - Leave **Enable staff uploads** **off**.
   - Enable **student OAuth uploads**.
   - Paste OAuth client ID and secret.
   - Leave **Workspace email domain** empty (allows Gmail).
5. Student: **Profile → Connect Google Drive** → upload a file in group chat with a resource name.

Staff file uploads stay disabled until Shared drive is configured.

---

## Full setup (Google Workspace)

### IT prerequisites

1. **Shared drive** for PowerHUB (e.g. “PowerHUB Files”).
2. **Service account** in the same GCP project as OAuth.
3. Add the service account email as **Content manager** on the Shared drive.
4. Teachers: **Contributor** on the Shared drive (via Google Groups or direct membership).
5. Org policy: allow **anyone with the link** for files the app creates (or plan domain-only sharing in Phase 3).

### Admin configuration

1. **Administration → File storage** (or Django admin → Google workspace storage config).
2. **Staff section:** enable uploads, paste Shared drive ID, service account JSON.
3. **Save** → **Test Shared drive connection** → **Ensure PowerHUB root folder**.
4. **Students section:** OAuth client ID/secret, redirect URI, optional domain restriction.
5. Monitor **Student Google connections** and **Recent upload log** on the same page.

Credentials are **encrypted in the database** — rotation does not require redeploy.

### Folder layout

```
Shared drive (or My Drive root)
└── PowerHUB/
    └── Groups/
        └── {cohort} — {group name}/
            └── {uploaded files}
```

Folder IDs are cached in `GoogleDriveFolder` (visible under “Cached Drive folder mappings” on the admin page).

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Staff upload fails | SA on Shared drive as Content manager; `is_enabled`; drive ID correct |
| Student cannot connect | `student_oauth_enabled`; redirect URI matches GCP; OAuth email = PowerHUB email |
| Upload stuck “pending” | Celery **worker** running; Redis up |
| Upload failed | Error in chat bubble; **Retry upload** if staged file exists; see upload log |
| Resource tile missing link | Upload must reach `ready`; resource name required on post |

---

## Local development

```bash
docker compose up --build
```

Requires **web**, **worker**, **redis**, and **migrate** services. Configure storage in the UI after `createsuperuser`.

See [SETUP.md](SETUP.md) for full local stack.

---

## Production checklist

- [ ] `SITE_URL` matches OAuth redirect host
- [ ] Celery worker + beat on Render (or equivalent)
- [ ] Staff Shared drive + SA (when using teacher uploads)
- [ ] Student OAuth tested end-to-end
- [ ] Backup / key rotation process for encrypted creds in DB

See [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).
