# Google Drive Integration — Final Architecture

## Goal

Store **chat file uploads** in each user's **Google Drive** (Workspace domain account), not on PowerHUB `MEDIA_ROOT`. Resources remain a **link index**; opening a tile uses the user's existing Google session in the browser.

## Product constraints (agreed)

| Rule | Detail |
|------|--------|
| Upload source | Group chat posts with file + `resource_label` (existing Resources sync rules) |
| Storage owner | Uploader's Google account |
| Folder layout | Auto-created app root folder + per-group subfolders under that root |
| Sharing on upload | **Anyone with the link** can view (`anyone` + `reader`) |
| Accounts | All users have org-domain Google accounts; PowerHUB `User.email` matches that domain |
| No local bytes | New chat uploads do not write to `Post.file` / `media/group_files/` |
| Link-only posts | Pasted URLs (including existing Drive links) unchanged — no re-upload |

Supersedes the removed storage comparison doc — **per-user Drive** only in v1 (not a separate company shared drive).

---

## High-level architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│  UI: Group chat composer / Profile (Connect Google)             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Application layer                                               │
│  • GoogleConnectService (OAuth)                                  │
│  • DriveFolderService (ensure PowerHUB tree)                     │
│  • DriveUploadService (multipart upload + permissions)           │
│  • GroupPostStorageOrchestrator (chat save hook)                 │
│  • resources.sync_from_group_post (url = webViewLink)            │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Infrastructure                                                  │
│  • Google OAuth2 + token refresh                                 │
│  • Drive API v3 client                                           │
│  • Encrypted token store (PostgreSQL)                            │
│  • Celery task for upload (recommended)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Google Workspace (user Drive)                                   │
│  PowerHUB/                                                       │
│    └── Groups/                                                   │
│          └── {cohort}-{group}/  ← files from that group's chat   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data model

## 1) `GoogleAccountConnection` (1:1 `accounts.User`)

| Field | Purpose |
|-------|---------|
| `user` | OneToOne |
| `google_subject` | Stable Google user id |
| `google_email` | Must match `User.email` (normalized) |
| `access_token_encrypted` | Short-lived |
| `refresh_token_encrypted` | Long-lived |
| `token_expires_at` | Refresh scheduling |
| `scopes_granted` | Audit |
| `root_folder_id` | Drive id of `PowerHUB` folder |
| `connected_at` / `disconnected_at` | Lifecycle |
| `last_error` | Support |

Constraint: unique `google_subject`; unique active connection per user.

## 2) `GoogleDriveFolder` (mapping cache)

| Field | Purpose |
|-------|---------|
| `user` | Owner |
| `folder_kind` | `root` \| `group` |
| `group` | FK nullable (for `group` kind) |
| `drive_folder_id` | Google folder id |
| `drive_path` | Display path cache e.g. `PowerHUB/Groups/Bern-2026` |

Unique: (`user`, `folder_kind`, `group`).

## 3) Extend `group_space.Post`

| Field | Purpose |
|-------|---------|
| `drive_file_id` | Google file id |
| `drive_web_view_link` | Canonical open URL for Resources |
| `drive_upload_status` | `pending` \| `ready` \| `failed` |
| `drive_upload_error` | Last error message |

Deprecate for **new** uploads: `Post.file` (keep column for legacy rows during migration).

## 4) `ResourceItem` (minimal change)

- `url` = `drive_web_view_link` when present, else existing URL/file logic.
- Optional: `storage_backend` = `google_drive` \| `external_url` \| `legacy_local`.
- Optional: `drive_file_id` denormalized for admin/debug.

---

## OAuth and security

## Scopes (recommended)

- `openid`, `email` — verify identity
- `https://www.googleapis.com/auth/drive.file` — create/access files and folders **created by this app** only (least privilege)

Do **not** request full `drive` scope unless IT explicitly requires browsing arbitrary user files.

## Connect flow

1. User opens **Profile → Google Drive**.
2. `GET /accounts/google/connect/` → Google consent screen.
3. Callback validates:
   - `google_email` equals `User.email` (case-insensitive).
   - Hosted domain matches org policy (`hd` claim or allowlist env).
4. Create `PowerHUB` root folder if missing; store `root_folder_id`.
5. Mark connection active.

## Enforcement

- **Chat file attach** blocked until Google connected (clear CTA to connect).
- Paste link-only posts still allowed without OAuth.
- Token refresh on upload; on `invalid_grant` → mark disconnected, notify user to reconnect.

## Secrets

- Client id/secret in env (`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`).
- Tokens encrypted at rest (Fernet/KMS pattern same as planned Slack tokens).
- Never log tokens or file contents.

---

## Folder layout (per user)

```text
My Drive/
  PowerHUB/                          ← root_folder_id (once per user)
    Groups/
      {cohort_slug}-{group_name}/      ← one folder per cohort group user posts in
        2026-06-02_slides-week3.pdf
        ...
```

Rules:

- Root `PowerHUB` created on first successful connect (or first upload).
- Group subfolder created lazily on first upload to that group.
- Folder names sanitized; internal mapping via `GoogleDriveFolder`, not by display name alone.

Optional later: `PowerHUB/Personal/` for non-group uploads (out of v1 scope).

---

## Upload pipeline (chat → Drive → Resources)

Triggered from `group_space.views.message_create` after validation (file + `resource_label`).

### Synchronous path (small files only, optional)

1. Ensure connection + folders.
2. Upload bytes to Drive (`files.create` with `parents=[group_folder_id]`).
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

## Teacher / admin (v1)

Same as students: files land in **uploader's** `PowerHUB/Groups/...` with link sharing.

Optional **v2** (not v1): org **Shared drive** for official curriculum uploads only — separate folder mapping table and service account or delegated admin account. Out of scope for initial rollout.

---

## UI placement

| Location | Change |
|----------|--------|
| `accounts/profile/` | Google Drive: Connected / Connect / Reconnect; connected email; test link |
| Group chat composer | File attach requires Google connected; uploading state on bubble |
| Resources item | Badge: **Google Drive** vs **Link** vs **Legacy file** |
| First login onboarding | If no connection, prompt before first file upload (not blocking text-only chat) |

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
| Not connected | Block upload; link to profile connect |
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

- Models: `GoogleAccountConnection`, `GoogleDriveFolder`, Post drive fields
- OAuth connect/disconnect + email/domain validation
- Folder provisioner (`PowerHUB`, group subfolder)

### Phase 1 — Chat upload MVP

- Celery upload task + permission `anyone` reader
- Chat UI: connect gate + pending/ready states
- Resources sync uses `webViewLink`
- Disable new writes to `Post.file`

### Phase 2 — Hardening

- Retry policy, rate limits, upload size aligned with chat limits
- Admin dashboards + IT runbook (Workspace sharing policy)
- Link health checks (optional)

### Phase 3 — Extensions (optional)

- Google Picker for manual Resources items
- Org shared drive for teachers
- Migrate legacy local files

---

## Acceptance criteria (v1 complete)

1. Student with org email can connect Google once from profile.
2. Chat file + resource name uploads to `PowerHUB/Groups/{group}/` in **their** Drive.
3. File is shared **anyone with link** automatically.
4. Group Resources tile shows working `webViewLink`; group members can open in browser with Google session.
5. No new files written under `media/group_files/`.
6. OAuth email must match PowerHUB `User.email`.
7. Failed uploads do not create misleading Resource items.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth client |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth secret |
| `GOOGLE_OAUTH_REDIRECT_URI` | Callback URL |
| `GOOGLE_WORKSPACE_HD` | Expected hosted domain (e.g. `powercoders.org`) |
| `GOOGLE_DRIVE_ROOT_FOLDER_NAME` | Default `PowerHUB` |
| `TOKEN_ENCRYPTION_KEY` | Encrypt refresh tokens |

---

## Open decisions for IT

1. Confirm Workspace allows **anyone with link** for student-uploaded files.
2. Confirm OAuth app verification / internal app publishing in Google Admin.
3. Max upload size (keep 10 MB or raise for Drive-only).
4. Whether anonymous link viewers are acceptable or domain-only link sharing is required (would change permission payload to `type=domain`).

If domain-only is required later, replace `anyone` with `type=domain` + `domain=...` while keeping the same architecture.
