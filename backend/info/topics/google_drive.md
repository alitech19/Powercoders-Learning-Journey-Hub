Google Drive stores group chat attachments and syncs named resources to each group’s Resources list.

## Who uses what {#overview}

| Role | Where files go | How |
|------|----------------|-----|
| **Student** | Their **My Drive** (`PowerHUB/Groups/…`) | Connect Google on **Profile** (OAuth) |
| **Teacher / admin** | Org **Shared drive** | Service account — no personal Google login |

Files are shared **anyone with the link** so classmates can open staff uploads without Shared drive membership.

**Important:** staff Shared drive and student OAuth are **separate**. Enabling staff uploads does **not** enable student Connect on Profile.

## For students {#students}

1. Open **Profile** → **Connect Google Drive** (only after admin completes OAuth setup below).
2. Sign in with the Google account whose **email matches** your PowerHUB login email.
3. In group chat, attach a file or create a **New Google file**; set a **resource name** to add it to Resources.

If upload fails, use **Retry upload** on the message (while the temporary copy still exists).

## Admin overview {#admin}

<!-- role: admin -->

Open **Administration → File storage**.

| Path | When |
|------|------|
| **Student OAuth only (MVP)** | Test with Gmail before IT gives Workspace + Shared drive |
| **Staff Shared drive** | When IT provides service account + org Shared drive |

Credentials live **in the database** (encrypted), not in `.env`. After changes: **Save** → **Validate OAuth config** (students) or **Test Shared drive connection** (staff).

Repo doc with the same steps: `docs/GOOGLE_DRIVE_SETUP.md`.

## Student OAuth — Google Cloud {#student-oauth-gcp}

<!-- role: admin -->

OAuth **Client ID** and **Client secret** come from [Google Cloud Console](https://console.cloud.google.com/) — not from PowerHUB.

### 1. Project and API

1. **Select a project** → **New project** (e.g. `powerhub-dev`).
2. **APIs & Services → Library** → search **Google Drive API** → **Enable**.

### 2. OAuth consent screen

**APIs & Services → OAuth consent screen**

| Field | Local / MVP testing |
|-------|---------------------|
| User type | **External** |
| App name | e.g. `PowerHUB Dev` |
| User support email | Your Gmail |
| Developer contact | Your email |

If app status is **Testing**, add every student under **Test users** — Google email must match their PowerHUB `User.email`.

### 3. OAuth client ID + secret

**APIs & Services → Credentials → Create credentials → OAuth client ID**

| Field | Value |
|-------|--------|
| Application type | **Web application** |
| Name | e.g. `PowerHUB local` |
| Authorized redirect URIs | See **Suggested** on File storage page, typically `http://localhost:8000/accounts/google/callback/` |

After **Create**, copy:

- **Client ID** — e.g. `123456789-xxxx.apps.googleusercontent.com`
- **Client secret** — shown **once**; copy immediately

Lost the secret? **Credentials** → open the client → **Add secret** (new one), then update PowerHUB.

### 4. Scopes (required)

**APIs & Services → OAuth consent screen → Data access → Add or remove scopes**

Add **Google Drive API**:

- `…/auth/drive.file` — *See, edit, create, and delete only the specific Google Drive files you use with this app*

Without this scope, connect fails with “did not grant Drive file access”. If you connected before adding the scope, revoke the app at [myaccount.google.com/permissions](https://myaccount.google.com/permissions) and connect again from Profile.

## Student OAuth — PowerHUB {#student-oauth-powerhub}

<!-- role: admin -->

On **Administration → File storage → Students (My Drive)**:

1. **Enable student OAuth uploads** — required; separate from staff Shared drive checkbox.
2. **OAuth client ID** — from Google Cloud step 3.
3. **OAuth client secret** — from Google Cloud step 3 (re-enter when rotating).
4. **Redirect URI** — must **exactly** match GCP (trailing slash, `http` vs `https`). Copy **Suggested** from this page into GCP **and** this field.
5. **Workspace email domain** — leave **empty** for Gmail MVP; set e.g. `powercoders.ch` to restrict sign-in later.
6. **Save settings** → **Validate OAuth config**.

`student_uploads_enabled` needs all three: checkbox + client ID + secret saved.

Ensure `.env` has `SITE_URL` matching your host (e.g. `http://localhost:8000` locally) so the suggested redirect URI is correct.

Student flow: **Profile → Connect Google Drive** → group chat upload with resource name.

## Staff Shared drive — Google Workspace {#workspace-shared-drive}

<!-- role: admin -->

Org **Shared drive** is created in **Google Workspace** (not in PowerHUB). PowerHUB uploads teacher/admin chat files there via a **service account**.

### 1. Create the Shared drive (Workspace admin)

1. Sign in as **Google Workspace admin** → [admin.google.com](https://admin.google.com/) or [drive.google.com](https://drive.google.com/).
2. **Shared drives** → **New** (e.g. name: `PowerHUB Files`).
3. Note the drive for teachers:
   - **Teachers / admins:** add as **Contributor** (create/edit; cannot delete files uploaded by the app service account).
   - **IT / PowerHUB admin:** **Content manager** or **Manager** on the drive.

Tip: use a **Google Group** (e.g. `teachers@yourdomain.org`) as Contributor so new teachers get access automatically.

### 2. Org policies (IT)

Confirm Workspace allows what PowerHUB needs:

| Policy | Why |
|--------|-----|
| **Google Drive API** enabled for the org | API calls from GCP |
| **Link sharing** allowed for new files | App sets **anyone with the link** so students open staff files without Shared drive membership |
| **Shared drives** enabled | Users can access the team drive |

If uploads succeed but students cannot open links, check admin restrictions on **external** or **anyone with the link** sharing.

### 3. Shared drive ID

Open the Shared drive in the browser. The URL contains the id:

```text
https://drive.google.com/drive/folders/0ABC…xyz
```

Copy the folder segment after `/folders/` → paste into PowerHUB **Shared drive ID**.

(Alternative: Drive API / admin reports — the web URL is usually enough.)

### 4. Teacher access (ongoing)

| Role | Shared drive role | PowerHUB |
|------|-------------------|----------|
| Teacher | **Contributor** on Shared drive | Uploads via PowerHUB chat → org drive; no personal Google connect required |
| Admin | **Content manager** on Shared drive | Can delete org-drive files in PowerHUB |
| Departed teacher | Remove from group / drive membership | **Files remain** in Shared drive |

## Staff — service account (Google Cloud) {#staff-service-account-gcp}

<!-- role: admin -->

The **service account JSON** comes from [Google Cloud Console](https://console.cloud.google.com/) — often the **same GCP project** as student OAuth.

### 1. Project + API

1. Use existing project (e.g. `powerhub-prod`) or create one linked to the org.
2. **APIs & Services → Library** → **Google Drive API** → **Enable**.

### 2. Create service account

1. **IAM & Admin → Service accounts → Create service account**
2. Name e.g. `powerhub-drive-uploader` → **Create and continue**
3. **Role:** no project IAM role is strictly required if the SA is added **directly on the Shared drive** (recommended). Skip extra roles unless your security policy requires them.
4. **Done** → open the service account → **Keys → Add key → Create new key → JSON**
5. Download the `.json` file — this is what you paste into PowerHUB (**shown once**; store securely).

The JSON contains `client_email` like:

```text
powerhub-drive@your-project.iam.gserviceaccount.com
```

### 3. Grant access on the Shared drive

1. In Google Drive, open the org **Shared drive**.
2. **Manage members** → add the **service account email** (not a human user).
3. Role: **Content manager** (app must create folders/files and set sharing).

Without this step, **Test Shared drive connection** in PowerHUB fails with permission errors.

### 4. Same project as student OAuth?

Yes. One GCP project can hold:

- OAuth Web client (students)
- Service account (staff Shared drive)

Enable **Drive API** once.

## Staff — PowerHUB {#staff-shared-drive-powerhub}

<!-- role: admin -->

**Administration → File storage → Org Shared drive (staff)**:

1. **Enable staff uploads to org Shared drive** ✓
2. **Shared drive ID** — from Workspace step above
3. **Display name** — label only (e.g. `PowerHUB Files`)
4. **Root folder name** — default `PowerHUB` (app creates under the Shared drive)
5. **Service account JSON** — paste full key file contents
6. **Save settings**
7. **Test Shared drive connection** — must succeed before use
8. **Ensure PowerHUB root folder** — creates `PowerHUB/` and stores root folder id

`staff_uploads_enabled` needs: checkbox + Shared drive ID + service account JSON saved.

Teachers: group chat file / **New Google file** → files land in `PowerHUB/Groups/{group}/` on the **org drive**. No **Connect Google** on Profile required for staff.

## Students with Google Workspace {#student-oauth-workspace}

<!-- role: admin -->

When students use **org email** (`student@yourdomain.org`), not Gmail:

1. Complete **Student OAuth — Google Cloud** and **PowerHUB** sections above.
2. **OAuth consent screen:** prefer **Internal** (org only) if the GCP project is under the same Workspace org.
3. **Workspace email domain** on File storage: e.g. `yourdomain.org` (restricts which Google accounts can connect).
4. Student **Test users** not needed for Internal apps.
5. Student Google email must still **match** PowerHUB `User.email`.

You can run **staff Shared drive** and **student OAuth** together once both sides are configured.

## Staff Shared drive (summary) {#staff-shared-drive}

<!-- role: admin -->

Quick pointer: sections **Google Workspace**, **service account (Google Cloud)**, and **PowerHUB** above. Teachers do **not** connect personal Google on Profile for org uploads.

## Troubleshooting {#troubleshooting}

<!-- role: admin -->

| Symptom | Fix |
|---------|-----|
| Student profile: “not enabled yet” | Enable **student OAuth** + ID + secret; not the staff checkbox alone |
| `redirect_uri_mismatch` | Redirect URI identical in GCP and File storage; check `SITE_URL` |
| `access_denied` / app blocked | Add student to **Test users** on consent screen |
| Drive scope / callback warning | Add **drive.file** on consent screen → Data access; revoke app at myaccount.google.com/permissions |
| Email mismatch after connect | PowerHUB email must equal Google account email |
| Upload stuck “pending” | Celery **worker** + **redis** running |
| Validate OAuth fails | Secret empty or wrong; re-paste and Save |
| Test Shared drive fails | SA email added on Shared drive as **Content manager**; correct drive ID |
| Staff upload 403 / permission | Drive API enabled; SA JSON valid; SA not only in GCP IAM but on the **drive** |
| Students cannot open staff file link | Workspace policy blocks “anyone with the link”; adjust admin sharing rules |
| Teacher cannot delete org file in chat | By design — only **admin** deletes `shared_org` uploads |
| `staff_uploads_enabled` false after Save | Need checkbox + drive ID + SA JSON (not checkbox alone) |

## Limits {#limits}

- Max file size: **10 MB** (same as legacy chat uploads).
- Rate limit: **10 uploads per minute** per user.
- Failed uploads do not create misleading Resource links until Drive upload succeeds.
