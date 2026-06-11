# Google Drive Integration — Final Architecture

## Goal

Store **chat file uploads** in **Google Drive** (Workspace), not on PowerHUB `MEDIA_ROOT`. Resources remain a **link index**; opening a tile uses the user's browser Google session.

**Hybrid storage (agreed with org teachers):**

| Who uploads | Where files live | Why |
|-------------|------------------|-----|
| **Staff** (`teacher`, `admin`) | Org **Shared drive** (team folder) — one `PowerHUB/Groups/…` tree | New teachers inherit Shared drive access automatically; files **stay** when someone leaves |
| **Students** | Uploader's **My Drive** — `PowerHUB/Groups/…` under their account | Student work stays tied to the student; OAuth per user |

## Product constraints (agreed)

| Rule | Detail |
|------|--------|
| Upload source | Group chat posts with file + `resource_label` (existing Resources sync rules) |
| Staff storage | Shared drive folder provisioned by app (service account); **not** uploader's personal My Drive |
| Student storage | Uploader's My Drive via OAuth (`drive.file` scope) |
| Folder layout | Same logical path under both backends: `PowerHUB/Groups/{cohort}-{group}/` |
| Sharing on upload | **Anyone with the link** can view (`anyone` + `reader`) so students can open staff files without Shared drive membership |
| Accounts | Org-domain Google; student OAuth email must match `User.email` |
| Staff OAuth | **Not required** for chat file upload (PowerHUB auth + service account is enough) |
| Staff on Shared drive | **Contributor** — read + add/edit; **cannot delete** files uploaded by the app (service account) |
| Admin on Shared drive | **Content manager** — full delete in Drive + delete in PowerHUB |
| Delete in PowerHUB | **Admin only** for `shared_org` files; student personal files: author or admin |
| No local bytes | New chat uploads do not write to `Post.file` / `media/group_files/` |
| Link-only posts | Pasted URLs unchanged — no re-upload |
| Admin config | **All** Google integration credentials & ids in DB — editable via **web admin page + Django admin**; **no** `GOOGLE_*` in `.env` |

---

## High-level architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│  UI: Group chat composer                                         │
│  Profile → Connect Google (students only, for file upload)       │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  GroupPostStorageOrchestrator                                    │
│    if author.role in (teacher, admin) → staff path               │
│    else → student path                                           │
└──────────────┬──────────────────────────────┬────────────────────┘
               │                              │
┌──────────────▼──────────────┐   ┌───────────▼────────────────────┐
│ SharedDriveUploadService    │   │ PersonalDriveUploadService       │
│ • Service account creds     │   │ • GoogleConnectService (OAuth)   │
│ • SharedDriveFolderService  │   │ • DriveFolderService (My Drive)  │
│ • supportsAllDrives=true    │   │ • User refresh token             │
└──────────────┬──────────────┘   └───────────┬────────────────────┘
               │                              │
               └──────────────┬───────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────┐
│  Celery: upload_post_file_to_drive(post_id)                       │
│  → permissions.create (anyone, reader)                           │
│  → resources.sync_from_group_post (webViewLink)                  │
└─────────────────────────────┬────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
┌───────────────────────┐                 ┌───────────────────────┐
│ Org Shared drive      │                 │ Student My Drive      │
│ PowerHUB/Groups/…     │                 │ PowerHUB/Groups/…     │
│ (org-owned, survives  │                 │ (per student OAuth)   │
│  staff turnover)      │                 │                       │
└───────────────────────┘                 └───────────────────────┘
```

---

## Data model

## 1) `GoogleWorkspaceStorageConfig` (singleton — **only** config source)

One row per deployment (`pk=1`). **No Google settings in environment variables.** Admins paste / update values in the app; changes apply without redeploy.

| Field | Purpose |
|-------|---------|
| `is_enabled` | Master switch (staff → Shared drive path) |
| **Shared drive (staff)** | |
| `shared_drive_id` | Google Shared drive id |
| `shared_drive_name` | Display label |
| `shared_root_folder_id` | `PowerHUB` folder id (set by “Ensure root folder”) |
| `root_folder_name` | Default `PowerHUB` |
| `service_account_email` | Read-only, parsed from JSON on save |
| `service_account_json_encrypted` | Full SA key JSON (encrypted) |
| **Student OAuth** | |
| `student_oauth_enabled` | Gate student My Drive uploads |
| `oauth_client_id` | Google OAuth Web client id |
| `oauth_client_secret_encrypted` | OAuth client secret (encrypted) |
| `oauth_redirect_uri` | Callback URL (default `SITE_URL` + `/accounts/google/callback/`; editable) |
| `workspace_hosted_domain` | Expected `hd` / email domain (e.g. `powercoders.org`) |
| **Diagnostics** | |
| `last_health_check_at` / `last_health_ok` / `last_error` | Health / test connection |
| `updated_at` / `updated_by` | Audit |

**Runtime:** `get_workspace_storage_config()` loads singleton (short cache; invalidate on save). Upload/OAuth code **never** reads `os.environ` for Google.

**Encryption at rest:** SA JSON, OAuth secret, student refresh tokens — Fernet key **derived from Django `SECRET_KEY`** (no separate `TOKEN_ENCRYPTION_KEY` env).

**Separate model:** per-user student tokens remain in `GoogleAccountConnection`.

## 2) `GoogleAccountConnection` (1:1 `accounts.User`) — **students**

| Field | Purpose |
|-------|---------|
| `user` | OneToOne |
| `google_subject` | Stable Google user id |
| `google_email` | Must match `User.email` (normalized) |
| `access_token_encrypted` / `refresh_token_encrypted` | OAuth tokens |
| `token_expires_at` | Refresh scheduling |
| `root_folder_id` | My Drive `PowerHUB` folder id |
| `connected_at` / `disconnected_at` / `last_error` | Lifecycle |

Staff **may** connect optionally later (Picker, diagnostics); **not** required for staff file upload.

## 3) `GoogleDriveFolder` (mapping cache)

| Field | Purpose |
|-------|---------|
| `storage_backend` | `shared_org` \| `personal` |
| `user` | Nullable — set for `personal`; null for `shared_org` |
| `folder_kind` | `root` \| `group` |
| `group` | FK nullable (for `group` kind) |
| `drive_folder_id` | Google folder id |
| `drive_path` | Display cache e.g. `PowerHUB/Groups/Bern-2026` |

Unique: (`storage_backend`, `user`, `folder_kind`, `group`) with null-safe uniqueness for org rows.

## 4) Extend `group_space.Post`

| Field | Purpose |
|-------|---------|
| `drive_storage_backend` | `shared_org` \| `personal` \| empty (legacy) |
| `drive_file_id` | Google file id |
| `drive_web_view_link` | Canonical open URL for Resources |
| `drive_upload_status` | `pending` \| `ready` \| `failed` |
| `drive_upload_error` | Last error message |

Deprecate for **new** uploads: `Post.file` (keep column for legacy rows).

## 5) `ResourceItem` (minimal change)

- `url` = `drive_web_view_link` when present, else existing URL/file logic.
- `storage_backend` = `google_drive_shared` \| `google_drive_personal` \| `external_url` \| `legacy_local`.
- Optional: `drive_file_id` denormalized for admin/debug.

---

## OAuth and security

## Scopes (recommended)

- `openid`, `email` — verify identity
- `https://www.googleapis.com/auth/drive.file` — create/access files and folders **created by this app** only (least privilege)

Do **not** request full `drive` scope unless IT explicitly requires browsing arbitrary user files.

## Connect flow (students)

1. Student opens **Profile → Google Drive**.
2. `GET /accounts/google/connect/` → Google consent screen.
3. Callback validates `google_email` == `User.email` and hosted domain (`workspace_hosted_domain` from config).
4. Create `PowerHUB` root folder in **My Drive** if missing; store `root_folder_id`.

## Enforcement

| Role | File attach in chat |
|------|---------------------|
| **Student** | Blocked until Google connected (CTA to profile) |
| **Teacher / admin** | Allowed without personal OAuth — upload uses **service account** → Shared drive |
| **All** | Link-only posts allowed without OAuth |

Student token refresh on upload; on `invalid_grant` → disconnected, reconnect prompt.

## Secrets

- **Google credentials live in PostgreSQL** (encrypted fields on `GoogleWorkspaceStorageConfig`).
- Editable by **admin** via PowerHUB **Сховище файлів** and **Django admin** (same model).
- Mask secrets in UI (show last 4 chars); re-paste to rotate.
- Never log tokens, JSON keys, or file contents.
- Rotating `SECRET_KEY` requires re-saving encrypted fields (document in runbook) or a one-off re-encrypt management command.

---

## Folder layout

Same **logical** tree in two places:

### Org Shared drive (staff uploads)

```text
Shared drive: "Powercoders Curriculum" (example name — IT chooses)
  PowerHUB/                              ← shared_root_folder_id (once)
    Groups/
      {cohort_slug}-{group_name}/
        2026-06-02_slides-week3.pdf      ← uploaded by any teacher/admin
```

- Created/maintained by **service account** with Content manager (or equivalent) on the Shared drive.
- New teachers: access via **Shared drive membership** (Workspace admin), not per-file ACL churn.
- Departing staff: files remain in Shared drive.

### Student My Drive (student uploads)

```text
My Drive/
  PowerHUB/                              ← per student, on OAuth connect
    Groups/
      {cohort_slug}-{group_name}/
        ...
```

Rules (both backends):

- Group subfolder created lazily on first upload to that group.
- Folder names sanitized; mapping in `GoogleDriveFolder`, not by display name alone.
- Drive API: staff path uses `supportsAllDrives=true`, `driveId` / shared parent ids.

---

## Upload pipeline (chat → Drive → Resources)

Triggered from `group_space.views.message_create` after validation (file + `resource_label`).

**Route by role:** `teacher` / `admin` → `SharedDriveUploadService`; `student` → `PersonalDriveUploadService` (requires OAuth).

### Synchronous path (small files only, optional)

1. Ensure folders (Shared drive SA or student connection).
2. Upload bytes to Drive (`files.create` with `parents=[group_folder_id]`; `supportsAllDrives=true` on staff path).
3. `permissions.create`: `type=anyone`, `role=reader`, `allowFileDiscovery=false`.
4. Set `drive_web_view_link`, `drive_file_id`, `drive_upload_status=ready`.
5. Call `after_post_saved(post)` → `sync_from_group_post` sets `ResourceItem.url`.

### Recommended: async path (Celery)

1. Create `Post` immediately with `drive_upload_status=pending`, body/label as today.
2. Enqueue `upload_post_file_to_drive(post_id)`.
3. Chat bubble shows “Uploading to Drive…” then HTMX poll or trigger refresh on success.
4. On success: update post, sync Resources.
5. On failure: `failed` + user-visible retry; no `ResourceItem` until `ready`.

Keeps chat responsive and avoids Gunicorn timeout on large files.

### Permission policy (fixed)

After every successful `files.create`:

```text
permissions.create(fileId)
  type: anyone
  role: reader
  allowFileDiscovery: false
```

This matches **anyone with the link** — cohort members open the tile in Resources while logged into any Google account (or anonymous view if org policy allows link access).

**Org note:** Workspace admin can restrict “anyone with link” via admin policy. IT must allow this sharing mode for the integration to work as designed.

---

## Resources sync (unchanged rules, new URL source)

`resources.services.resource_url_for_post`:

1. If `post.drive_web_view_link` → use it.
2. Else first URL in body.
3. Else legacy `post.file.url` (migration period only).

`sync_from_group_post` logic unchanged: qualifying posts → group system container, badge **Group chat**.

---

## Access in browser (“same browser Google login”)

PowerHUB does **not** implement a separate Google login for viewing.

| Step | Behavior |
|------|----------|
| User clicks Resources link | Opens `drive_web_view_link` in new tab |
| Browser has active Google session | Google grants access if link permission applies |
| Wrong Google account | Google shows account picker / request access |
| Not logged in | Google sign-in page (same browser) |

Implementation requirement: store and open **`webViewLink`**, not export/download URLs, for Docs/Sheets/PDFs.

---

## Staff uploads — service account (technical)

IT provisions (or admin follows dev runbook below):

1. **Shared drive** with dedicated `PowerHUB/` subtree.
2. **Service account** — **Content manager** on Shared drive (upload, delete via API).
3. **Workspace group membership** on Shared drive (see permissions table).

Upload flow for staff:

1. `SharedDriveFolderService.ensure_group_folder(group)` under org `PowerHUB/Groups/…`.
2. `files.create` with `parents=[group_folder_id]`, `supportsAllDrives=true` — file attributed to **SA**, not teacher.
3. `permissions.create` — **anyone with link** (reader) for student access via Resources.
4. Record `drive_storage_backend=shared_org` on `Post`.

Alternative rejected: OAuth upload to teacher's My Drive — files leave with the person.

---

## Shared drive permissions (org + app)

### Google Workspace membership (manual / IT — once per org)

| PowerHUB role | Shared drive role | Read | Write (add/edit) | Delete in Drive UI |
|---------------|-------------------|------|------------------|-------------------|
| **Teacher** | **Contributor** | Yes | Yes | Only files **they** uploaded directly in Drive — **not** files uploaded via PowerHUB (SA owner) |
| **Admin** (`Role.ADMIN`) | **Content manager** | Yes | Yes | Yes — any file in drive |
| **Student** | *(none)* | Via link / Resources | — | — |

PowerHUB uploads for staff always go through the **service account**, so teachers get write access to the folder tree but **cannot remove** curriculum files created by the app. Admins retain delete in Drive and in PowerHUB.

### PowerHUB application rules

| Action | Teacher | Admin |
|--------|---------|-------|
| Upload file in group chat (staff path) | Yes | Yes |
| Edit post / replace file | Yes (author) | Yes |
| Delete chat post with `shared_org` file | **No** | **Yes** |
| Delete `ResourceItem` linked to `shared_org` | **No** | **Yes** |
| Delete student `personal` drive file | **No** (v1) | Yes |
| Call Drive `files.delete` API | Never (teacher) | Admin only, via SA client |

Implementation: `can_delete_drive_artifact(user, post|item)` → `user_is_admin(user)` when `storage_backend` is `shared_org`; student personal → author or admin.

Audit: log admin deletes (`AuditLog`).

**Limitation:** A teacher with Contributor who uploads **directly in Google Drive UI** (bypassing PowerHUB) could delete **that** upload. Policy: use PowerHUB for staff uploads; optional v2 restrict Shared drive to SA-only write (advanced).

---

## Admin storage settings (configuration UI)

**Who:** `Role.ADMIN` only.

**Where (both edit the same singleton):**

| Surface | Path |
|---------|------|
| **PowerHUB web** | `/accounts/storage/` — **Сховище файлів** in **Адміністрування ▾** ([ADMIN_RESTRUCTURE_PLAN.md](ADMIN_RESTRUCTURE_PLAN.md)) |
| **Django admin** | `Google workspace storage` under **Core platform** (custom admin index) |

First-time setup: admin logs in → opens **Сховище файлів** → pastes credentials from Google Cloud Console → **Save** → **Test connection** → **Ensure root folder**. No server restart, no `.env` edit.

### PowerHUB web form sections

| Section | Fields / actions |
|---------|------------------|
| **General** | Master enable toggle |
| **Org Shared drive (staff)** | Shared drive ID · display name · SA JSON textarea (paste once, masked after save) · **Test connection** · **Ensure `PowerHUB` root folder** |
| **Students (My Drive)** | OAuth enabled · Client ID · Client secret (masked) · Redirect URI (prefilled from `SITE_URL`) · Allowed email domain |
| **Status** | Last health check · SA email · root folder id · copy redirect URI for Google Console |
| **Help** | Collapsible: link to manual Google Cloud + Shared drive setup (below) |

### Django admin

Same fields; use for support / emergency edit. Register `GoogleWorkspaceStorageConfig` with:

- `has_add_permission` → only if no row exists (singleton)
- `has_delete_permission` → False
- Read-only: `service_account_email`, health fields, `updated_by`

### Admin actions (backend)

| Action | Behaviour |
|--------|-----------|
| `test_connection` | Decrypt SA → list Shared drive → verify `shared_drive_id` |
| `test_oauth_config` | Validate client id/secret format; show redirect URI to register in Console |
| `ensure_root_folder` | Create `PowerHUB` under Shared drive if missing |
| `health_check` (optional Celery) | Nightly ping; set `last_health_ok` |

**Feature off:** if `is_enabled` is false, staff uploads fall back to error message (or legacy local until migration complete — dev only).

---

## Manual setup — development & testing

Use a **test Google Workspace** (or personal Google with Shared drive if available). Do **not** commit keys.

### 1) Google Cloud project

1. [Google Cloud Console](https://console.cloud.google.com/) → create project e.g. `powerhub-dev`.
2. **APIs & Services → Enable** `Google Drive API`.
3. **OAuth consent screen** (External or Internal) — for student connect testing.
4. **Credentials → Create credentials:**
   - **OAuth client ID** (Web application) — copy id + secret into **Сховище файлів** later.
   - **Service account** — download JSON → paste into **Сховище файлів** (not into `.env`).

### 2) Shared drive (manual)

1. Google Drive → **Shared drives → New** e.g. `PowerHUB Dev`.
2. Open drive → copy id from URL → paste in **Сховище файлів → Shared drive ID**.
3. **Manage members:**
   - Service account email → **Content manager**.
   - Test teacher Workspace users → **Contributor**.
   - Test admin user → **Content manager**.
4. (Optional) Create folder `PowerHUB` manually, or let app create on **Ensure root folder**.

### 3) Test Workspace users (manual)

Create in Admin console or use existing:

| Account | PowerHUB role | Shared drive role |
|---------|---------------|-------------------|
| `teacher-dev@yourdomain.test` | teacher | Contributor |
| `admin-dev@yourdomain.test` | admin | Content manager |
| `student-dev@yourdomain.test` | student | — (OAuth connect in profile) |

Create matching users in PowerHUB (`dev-login` or admin UI) with same emails.

### 4) PowerHUB admin UI (not `.env`)

1. Log in as admin → **Адміністрування → Сховище файлів**.
2. Paste: Shared drive ID, SA JSON, OAuth client id/secret, domain `yourdomain.test`.
3. Redirect URI: use value shown on form (register same URI in Google Console).
4. **Save** → **Test connection** → **Ensure root folder**.

### 5) Smoke test checklist

- [ ] All Google values configured **only** in admin UI (no `GOOGLE_*` in `.env`)
- [ ] Admin → Storage → Test connection OK
- [ ] Ensure root folder → `PowerHUB` appears in Shared drive
- [ ] Teacher uploads in chat → file in `PowerHUB/Groups/…`, Resources link works
- [ ] Teacher **cannot** delete that file in PowerHUB UI
- [ ] Admin **can** delete in PowerHUB
- [ ] Student connects OAuth → upload to My Drive path works

---

## UI placement

| Location | Change |
|----------|--------|
| `accounts/profile/` | **Students**: Connect / Reconnect; **staff**: note “Uploads use org Shared drive” |
| `accounts/storage/` | **Admin**: storage config (see above) |
| Group chat composer | Students: connect gate; staff: attach without OAuth; uploading state on bubble |
| Resources item | Badge: **Org drive** / **My Drive** / **Link** / **Legacy**; delete control admin-only for org drive |
| Student onboarding | Prompt connect before first file upload (text-only chat OK) |

---

## Migration from Option 1 (local `media/group_files/`)

| Phase | Action |
|-------|--------|
| 1 | Ship Drive upload for **new** posts only |
| 2 | `ResourceItem.storage_backend` distinguishes legacy |
| 3 | Optional batch job: copy old files to author's Drive (heavy; may skip and keep legacy URLs) |
| 4 | Remove `Post.file` usage in forms; read-only for old rows |

---

## Error handling

| Case | UX |
|------|-----|
| Student not connected | Block upload; link to profile connect |
| Shared drive / SA misconfigured | Staff upload fails with IT contact message |
| Email mismatch on OAuth | Error: use your `@org.domain` account |
| Quota exceeded | Retry later message |
| Sharing policy blocked by admin | Show IT contact message |
| Upload failed mid-flight | Post marked failed; retry button for author |
| Deleted on Drive manually | Resources link 404; optional periodic link health check (v2) |

---

## Observability

- `DriveUploadLog`: `post_id`, `user_id`, `status`, `duration_ms`, `error_code`
- Metrics: upload success rate, permission errors, token refresh failures
- Admin: list connections, last error, disconnect user

---

## Rollout phases

### Phase 0 — Foundation

- Models: `GoogleWorkspaceStorageConfig` (all creds in DB), `GoogleAccountConnection`, `GoogleDriveFolder`, Post drive fields
- `get_workspace_storage_config()` + Fernet encrypt/decrypt (from `SECRET_KEY`)
- Service account client + Shared drive folder provisioner
- **Admin storage settings** (web + Django admin) + test connection / ensure root folder
- Manual dev runbook: Google Cloud outside app; paste into admin UI (link from plan)
- Student OAuth connect/disconnect + email/domain validation
- Personal Drive folder provisioner (My Drive)

### Phase 1 — Chat upload MVP

- Celery task routes by `author.role` → shared vs personal upload service
- Permission `anyone` reader on all new files (student access to staff files)
- Chat UI: student connect gate; staff upload without OAuth; pending/ready states
- Resources sync uses `webViewLink` + `storage_backend` badge
- **Delete policy:** `can_delete_drive_artifact` — admin-only for `shared_org`
- Disable new writes to `Post.file`

### Phase 2 — Hardening

- Retry policy, rate limits, upload size
- Admin: list student connections, SA health, Shared drive folder ids
- IT runbook (Shared drive membership, sharing policy)
- Link health checks (optional)

### Phase 3 — Extensions (optional)

- Google Picker for manual Resources items
- Migrate legacy local files
- Domain-only link sharing if IT disables public links

---

## Acceptance criteria (v1 complete)

1. **Student** connects Google from profile; OAuth email matches `User.email`.
2. **Student** file + resource name → `PowerHUB/Groups/{group}/` in **their** My Drive.
3. **Teacher/admin** file + resource name → same logical path in **org Shared drive** (no personal OAuth).
4. New teachers (Contributor) browse/write Shared drive; departed staff files remain; teachers cannot delete SA-uploaded files in PowerHUB.
5. **Admin** can delete org-drive files in PowerHUB (and in Drive as Content manager).
6. Admin configures **everything** (drive id, SA JSON, OAuth, domain) in **Сховище файлів** + Django admin — no redeploy to rotate secrets.
7. All new files: **anyone with link**; Resources tile opens `webViewLink` for students.
8. No new files under `media/group_files/`.
9. Failed uploads do not create misleading Resource items.

---

## Environment variables

**None required for Google Drive.** All integration settings live in `GoogleWorkspaceStorageConfig` (admin UI).

Existing app env still used as today: `SITE_URL` (to suggest OAuth redirect URI), `SECRET_KEY` (encrypts stored secrets). No `GOOGLE_*` or `TOKEN_ENCRYPTION_KEY` in `.env`.

---

## Open decisions for IT

1. **Shared drive name** and whether to use existing shared space or new drive for `PowerHUB/`.
2. Service account: create new vs reuse; **Content manager** on Shared drive.
3. Workspace: all **teachers** → Shared drive **Contributor**; all **admins** → **Content manager** (manual group sync or IT process).
4. Confirm **anyone with link** allowed — required so students open staff-uploaded files without Shared drive membership.
5. OAuth internal app for student connect (redirect URI copied from **Сховище файлів**).
6. Max upload size (10 MB vs higher for Drive-only).
7. If link sharing must be **domain-only**, use `type=domain` instead of `anyone` (students still need org Google accounts).
