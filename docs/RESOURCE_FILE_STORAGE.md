# Resources — file storage comparison

PowerHUB stores **resource files and links** when group members post to chat with a **resource label** (badge **Resource** in the header). Those entries will sync to the **Resources** app (group tile grid). Achievement shares (journal / habit / goal / task snapshots) are **not** resources — chat only.

This document compares the **two approaches** we consider for where file bytes live.

Related: [APP_PLAN.md](APP_PLAN.md) (build #9 `resources`, backport B13).

---

## What counts as a resource

| Chat post type | Saved to Resources? | Storage question |
|----------------|---------------------|------------------|
| File + `resource_label` | Yes | Where the file bytes live |
| Link in message + `resource_label` | Yes | URL only — no upload |
| Plain text | No | — |
| Shared work snapshot | No | HTML in DB only |

**v1 behaviour (Group Space, done):** uploads go to **`media/group_files/`** on the server; links stay as URLs in `Post.body`. Sync to Resources is stubbed until the `resources` app lands.

---

## Option 1 — Local server storage (current)

**How it works**

- `Post.file` → Django `FileField(upload_to='group_files/%Y/%m/')` under `MEDIA_ROOT` (Docker volume `./backend/media`).
- Database stores path + `resource_label`; downloads via `/media/...` (production: prefer authenticated download view).
- External docs: user pastes a URL (e.g. Google Drive share link) in the message — no copy of the file on our server.

**Limits in code today**

- Max size: 10 MB (`GROUP_FILE_MAX_BYTES`)
- Extensions: `.pdf`, `.doc`, `.docx`, `.txt`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`
- File or link → `resource_label` required

### Pros

| | |
|--|--|
| **Speed to ship** | Already implemented for Group chat; no OAuth or Google API. |
| **Simple UX** | Attach in chat → download from the same app; links work as today. |
| **No Google required** | Students without Workspace can still share PDFs and images. |
| **One place for compliance** | Bytes, metadata, delete-with-post, export in our stack. |
| **Low ops complexity** | Same pattern as avatars (`media/avatars/`). |

### Cons

| | |
|--|--|
| **We own disk** | Capacity, backup, restore on our host or volume. |
| **Scale cost** | Many cohorts × many uploads → storage and egress. |
| **Security** | Size/MIME limits help; optional malware scan ([PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)). |
| **No live Google edit** | Uploaded file is a download, not an in-browser Doc. |
| **Horizontal scaling** | Multiple app containers need shared media or a later storage backend. |

### Best when

- v1 and near-term production on a single stack or modest traffic.
- Mix of Google links (paste URL) and small file uploads is acceptable.

---

## Option 2 — Google Drive (student + company)

**How it works**

- On attach (or “save to Resources”), the app uploads via **Google Drive API** instead of writing to `MEDIA_ROOT`.
- **Where the file lands depends on role:**

| Role | Drive target | Purpose |
|------|--------------|---------|
| **Student** | Student’s Google account (bootcamp / personal Workspace) | Own work, group-shared materials, portfolio |
| **Teacher / admin** | **Company** Google Workspace — org shared drive or team folder | Official curriculum, vetted resources, long-lived links |

- Post stores Drive `file_id`, share URL, and `resource_label`. Resources tiles open Drive (permissions per Google sharing rules).
- Pasted links without upload behave as today (URL only).

### Pros

| | |
|--|--|
| **No file bytes on PowerHUB** | Less disk, backup, and malware surface on our servers. |
| **Native Google workflow** | Edit Docs/Sheets/Slides in browser; familiar sharing. |
| **Workspace policies** | DLP, retention, admin visibility on **company** drive for teachers. |
| **Student ownership** | Files can live in the student’s Drive where that fits the programme. |
| **Long-lived curriculum** | Teachers maintain folders on the org shared drive. |

### Cons

| | |
|--|--|
| **Build cost** | OAuth consent, token refresh, error handling, UI for “connect Google”. |
| **Admin setup** | Shared drives, service accounts or domain-wide delegation; different flows for students vs staff. |
| **Broken or wrong sharing** | Revoked access, wrong “anyone with link”, user leaves org. |
| **Split data** | Metadata in PostgreSQL; files in Google — GDPR/export spans both. |
| **Dependency** | API quotas, Google outages, students without Google account. |
| **Fallback needed** | What happens when consent denied or upload fails? |

### Best when

- Organisation policy: **all documents must live in Google Workspace**.
- IT can own shared drives and OAuth; budget for integration and maintenance.

---

## Side-by-side

| Criterion | Option 1 — Local (current) | Option 2 — Google Drive |
|-----------|----------------------------|-------------------------|
| Status | **Implemented** in Group Space | Not started |
| Time to add | Done for chat; wire Resources sync | Large (OAuth + role-based targets) |
| File upload in app | Yes | Yes (via API) |
| Link-only resources | Yes | Yes |
| Server stores bytes | Yes | No |
| Student without Google | OK | Problematic |
| Teacher official materials | Same storage as students | Company shared drive |
| Edit in Google Docs | Only if user pasted Drive link | Yes for uploaded files |
| Ops burden | Medium (our disk/backups) | High (Google + our app) |

---

## Recommendation

| Phase | Choice |
|-------|--------|
| **Now (v1)** | **Option 1** — ship Resources app against existing local uploads and link posts. |
| **Later** | **Option 2** if product/IT commits to Workspace-only storage and admin support for student vs company drives. |

**Migration note:** Moving from Option 1 → 2 can apply to **new** uploads first; existing `media/group_files/` objects need migration or dual links during transition.

**Not in scope for this comparison:** S3/R2 object storage, “links only” (no upload), hybrid as a third product track — we deliberately keep the decision to these two product directions.
