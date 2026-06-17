# Slack integration setup

Operational guide for PowerHUB Slack: personal notification DMs, staff channel webhook, and optional group-chat channel sync.

Related: in-app **Administration → Slack integration** (ⓘ help) · `/info/slack_integration/` · notification schedules on **Administration → Notifications**

---

## Overview

| Stream | Purpose | Configured by |
|--------|---------|----------------|
| **Personal OAuth** | DMs to each user (tasks, goals, mentions, digests) | Admin → Slack integration; user → **Profile → Notification settings → Connect Slack** |
| **Staff webhook** | Posts to one shared channel (e.g. missing-reflection digest) | Admin → Slack integration |
| **Group chat sync** | Two-way mirror between Group Space and mapped Slack channels | Admin → Slack integration (bot + Events API) + per-space channel mapping |

Credentials are stored **encrypted in the database** (same pattern as Google Drive). No Slack secrets in `.env` — only `SITE_URL` must match your public URL for OAuth and Events API callbacks.

---

## MVP: personal notification DMs only

Use this to test assignment / deadline Slack DMs before enabling staff webhook or chat sync.

### A. Slack app

Console: [https://api.slack.com/apps](https://api.slack.com/apps)

1. **Create New App → From scratch** — name e.g. `PowerHUB`, pick your workspace.
2. **OAuth & Permissions → Redirect URLs** — add exactly:
   ```
   {SITE_URL}/accounts/slack/callback/
   ```
   Example local: `http://localhost:8000/accounts/slack/callback/`
3. **User Token Scopes** (not Bot Token Scopes):

   | Scope | Why |
   |-------|-----|
   | `chat:write` | Send DM text |
   | `im:write` | Open DM with the user |

4. **Settings → Basic Information → App Credentials** — copy **Client ID** and **Client Secret**.

### B. PowerHUB — Administration → Slack integration

1. **Enable personal Slack OAuth** ✓
2. **OAuth client ID** — from step A.4
3. **OAuth client secret** — from step A.4
4. **OAuth redirect URI** — must match Slack app exactly (use **Suggested** on the page)
5. **Save settings** → **Validate OAuth config**

Ensure `.env` (local) or Render env:

```env
SITE_URL=http://localhost:8000
```

### C. User test

1. Log in as a student or teacher.
2. **Profile → Notification settings → Connect Slack** (Slack consent screen).
3. Enable **Slack** master switch and per-event toggles.
4. Trigger an event (e.g. staff assigns a shared task) — DM should arrive via Celery **worker**.

Leave **staff webhook** and **chat sync** off until you need them.

---

## Staff channel webhook

For operational digests (weekly missing reflections, some staff-only pings) — **not** per-user DMs.

### A. Slack app

On the same app (or a separate internal app):

1. **Incoming Webhooks** → **On** → **Add New Webhook to Workspace**
2. Pick channel (e.g. `#powerhub-alerts`)
3. Copy URL (`https://hooks.slack.com/services/…`)

### B. PowerHUB

**Administration → Slack integration**:

1. **Enable staff webhook** ✓
2. Paste **Webhook URL**
3. **Save** → **Send test webhook message**

### C. Enable reflection digest

**Administration → Notifications** → enable **Reflection digest** and set schedule. Requires **beat** service running (see [DEPLOY.md](DEPLOY.md)).

---

## Group chat ↔ Slack channel sync

Optional two-way sync between **Group Space** chat and a Slack channel. Requires bot token + Events API signing secret.

### A. Slack app (bot)

1. **OAuth & Permissions → Bot Token Scopes**: `chat:write` (add `channels:history` / `groups:history` only if Slack prompts for Events API).
2. **Install to workspace** → copy **Bot User OAuth Token** (`xoxb-…`).
3. Invite bot to each mapped channel: `/invite @YourBot`
4. **Event Subscriptions** → **Enable**
   - **Request URL**: value shown on PowerHUB **Slack integration** page (`…/accounts/slack/events/`)
   - Subscribe to bot event **`message.channels`** (and `message.groups` for private channels if needed)
5. **Basic Information → Signing Secret** — copy for PowerHUB

### B. PowerHUB — Slack integration

1. **Enable group chat → Slack channel** ✓
2. **Bot token** (`xoxb-…`)
3. **Signing secret**
4. **Save** → optional **Send test bot message** (channel ID `C…`)

### C. Map each chat space

| Space | Where |
|-------|--------|
| Cohort group | **Administration → Cohorts & Groups** → edit group → Slack channel sync |
| Custom project space | **Administration → Group spaces** → space detail → Slack channel sync |

Channel ID: Slack → channel → **View channel details** → copy ID at bottom.

### D. Users posting from Slack

Authors must **Connect Slack** on their PowerHUB profile so `slack_user_id` matches. Inbound messages appear as normal chat rows; thread replies show **↪ in reply to**.

### Behaviour notes

- When channel sync is **on** for a space, personal Slack DMs for mentions / all-messages are **skipped** for that space (channel post is enough). In-app and email still follow user settings.
- Edits and deletes sync both ways when sync is enabled.
- PowerHUB replies stay flat in the feed but post to the **Slack thread** when the parent message is already synced.

---

## Notifications and Celery Beat

Slack DMs and digests are sent asynchronously (**worker**). Scheduled digests and deadline reminders need **beat** + periodic tasks.

| Task | Celery task | Typical schedule |
|------|-------------|------------------|
| Hourly deadline reminders | `accounts.tasks.run_deadline_reminders_task` | Hourly |
| Weekly missing-reflection digest | `accounts.tasks.notify_missing_reflections` | Weekly (staff webhook) |
| Hourly notification digests | `accounts.tasks.dispatch_hourly_notification_digests_task` | Hourly |
| Daily notification digests | `accounts.tasks.dispatch_daily_notification_digests_task` | Daily |

**Administration → Notifications** saves schedules and creates/updates Beat entries automatically.

Verify locally: `/admin/django_celery_beat/periodictask/`  
On Render: web + **worker** + **beat** services — see [DEPLOY.md](DEPLOY.md).

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| “Slack OAuth is not configured” | OAuth enabled + client ID/secret saved on **Slack integration** |
| `redirect_uri` mismatch | Slack redirect URL **exactly** matches PowerHUB field (scheme, host, trailing slash); `SITE_URL` correct |
| `invalid_scope` | User scopes `chat:write`, `im:write` — not bot-only |
| Webhook test fails | URL valid, webhook enabled, channel exists |
| DMs not arriving | User connected Slack; master Slack on; event enabled; **worker** running; not in quiet hours / digest bucket |
| Digest never posts | **Beat** running; task in Periodic tasks; reflection digest enabled in **Notifications** |
| Bot test fails | `xoxb` token; bot invited to channel; channel ID is `C…` not name |
| Events URL verification fails | Public HTTPS URL; signing secret saved; beat/web reachable from Slack |
| Slack → PH message missing | Poster connected Slack on profile; mapping enabled for channel |
| Secrets broken after deploy | `SECRET_KEY` rotation without re-entering encrypted fields — re-save on **Slack integration** |
| Channel sync on but still getting mention DMs | Expected — DMs suppressed when sync is on for that space |

---

## Local development

```bash
docker compose up --build
```

Requires **web**, **worker**, **redis**. **beat** needed for scheduled digests/reminders.

```bash
docker compose exec web python manage.py createsuperuser
```

Configure Slack in the app UI (admin login) — see [SETUP.md](SETUP.md).

---

## Production checklist

- [ ] `SITE_URL` is public HTTPS (matches OAuth redirect and Events URL)
- [ ] Celery **worker** running
- [ ] Celery **beat** running if using digests / deadline reminders
- [ ] OAuth end-to-end tested (connect + one DM)
- [ ] Staff webhook tested if using reflection digest
- [ ] Chat sync: Events URL verified in Slack app; bot in each mapped channel
- [ ] Django admin **Slack workspace configuration** reachable for support (optional)

See [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).
