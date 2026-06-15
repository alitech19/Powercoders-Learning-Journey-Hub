Google Drive stores group chat attachments and syncs named resources to each group’s Resources list.

## Who uses what {#overview}

| Role | Where files go | How |
|------|----------------|-----|
| **Student** | Their **My Drive** (`PowerHUB/Groups/…`) | Connect Google on **Profile** (OAuth) |
| **Teacher / admin** | Org **Shared drive** | Service account — no personal Google login |

Files are shared **anyone with the link** so classmates can open staff uploads without Shared drive membership.

## Students {#students}

1. Open **Profile** → **Connect Google Drive**.
2. Sign in with the Google account that matches your PowerHUB email.
3. In group chat, attach a file and set a **resource name** to add it to Resources.

If upload fails, use **Retry upload** on the message (while the temporary copy still exists).

## Administrators {#admin}

<!-- role: admin -->

Open **Administration → File storage** (third item after Student Progress).

- **MVP:** enable student OAuth only; leave staff Shared drive off until IT is ready.
- **Full:** service account JSON, Shared drive ID, test connection, ensure root folder.
- Monitor student connections and recent upload log on that page.

Detailed steps are in the repository doc `docs/GOOGLE_DRIVE_SETUP.md` (MVP without Workspace + full IT setup).

## Limits {#limits}

- Max file size: **10 MB** (same as legacy chat uploads).
- Rate limit: **10 uploads per minute** per user.
- Failed uploads do not create misleading Resource links until Drive upload succeeds.
