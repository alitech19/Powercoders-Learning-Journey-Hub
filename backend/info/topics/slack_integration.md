PowerHUB uses Slack in two ways: **personal DMs** (each user connects on Notification settings) and a **staff channel webhook** (operational digests).

Credentials are stored **encrypted in the database** (same approach as File storage). Configure everything on **Administration → Slack integration** — no `.env` variables are required. Use the **ⓘ** button on that page for this guide.

## Overview {#overview}

| Stream | Who sets it up | Who receives |
|--------|----------------|--------------|
| **Personal OAuth** | Admin on **Administration → Slack integration** | Each user who clicks **Connect Slack** |
| **Staff webhook** | Admin on the same page | One shared Slack channel |

## Admin quick start {#admin-quick-start}

<!-- role: admin -->

1. Open **Administration → Slack integration**.
2. Check the **Status** panel (OAuth ready, webhook ready, last test, redirect URI, callback path).
3. Complete **Personal Slack OAuth** and/or **Staff channel webhook** (see sections below).
4. Click **Save settings**.
5. Use **Validate OAuth config** and **Send test webhook message**.
6. Tell users to open **Profile → Notification settings → Connect Slack** (after OAuth is enabled).

Global schedules (deadline reminders, missing-reflection digest) are on **Administration → Notifications**.

## Personal Slack OAuth {#personal-oauth}

<!-- role: admin -->

Users (students, teachers, admins) connect **their own** Slack workspace account. PowerHUB sends **direct messages** for events they enabled in the notification matrix.

### 1. Create a Slack app

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**.
2. Name e.g. `PowerHUB Notifications`, pick your workspace.

### 2. OAuth & Permissions

**OAuth & Permissions** → **Redirect URLs** → add exactly:

`{SITE_URL}/accounts/slack/callback/`

Example local: `http://localhost:8000/accounts/slack/callback/`

**User Token Scopes** (not Bot Token Scopes):

| Scope | Why |
|-------|-----|
| `chat:write` | Send DM text |
| `im:write` | Open DM channel with the user |

### 3. Copy credentials into PowerHUB

**Settings → Basic Information → App Credentials**

| PowerHUB field | Slack source |
|----------------|--------------|
| OAuth client ID | **Client ID** |
| OAuth client secret | **Client Secret** |
| OAuth redirect URI | Same URL you added under Redirect URLs — use **Suggested** on the settings form if unsure |

The settings page also shows **User callback path** (`/accounts/slack/callback/`) and your saved redirect URI in **Status**.

On **Slack integration**: enable **Enable personal Slack OAuth**, paste values, **Save**, then **Validate OAuth config**.

### 4. Install / distribute the app

Users must authorize the app in a workspace they use. For a single org workspace, share the app install link from **Manage Distribution** or ask each user to connect from PowerHUB (they'll see Slack's consent screen).

### 5. User side

**Profile → Notification settings → Connect Slack**. Master **Slack** switch stays locked until connected. Per-event Slack checkboxes respect digest and quiet hours like email.

## Staff channel webhook {#staff-webhook}

<!-- role: admin -->

Used for **channel posts** (not DMs): weekly missing-reflection digest (`notify_missing_reflections`), and some legacy staff pings (e.g. new user created).

### 1. Create incoming webhook

1. [api.slack.com/apps](https://api.slack.com/apps) → your app (or a separate internal app).
2. **Incoming Webhooks** → **On** → **Add New Webhook to Workspace**.
3. Pick the staff channel (e.g. `#powerhub-alerts`).
4. Copy the URL (`https://hooks.slack.com/services/…`).

### 2. PowerHUB

On **Slack integration**: enable **Enable staff webhook**, paste URL, **Save**, **Send test webhook message**.

Enable the digest on **Administration → Notifications** → **Reflection digest enabled**.

## Security notes {#security}

<!-- role: admin -->

| Topic | Guidance |
|-------|----------|
| **Where secrets live** | Encrypted at rest with Fernet derived from `SECRET_KEY`. Only admins reach the settings page. |
| **vs `.env`** | Not used — configure in the admin UI only. Rotating `SECRET_KEY` without re-entering secrets breaks decryption — plan key rotation. |
| **Webhook URL** | Anyone with the URL can post to the channel — treat like a password. |
| **OAuth client secret** | Same sensitivity as any OAuth app secret. |
| **User tokens** | Stored encrypted per user in `SlackIntegration`; revoked on disconnect. |
| **Audit** | `updated_by` records who last changed workspace config. |

This is **comparable risk to Google Drive credentials in File storage**: slightly more exposure than pure env (DB backup includes ciphertext), mitigated by encryption, admin-only UI, and masked fields on edit.

## Troubleshooting {#troubleshooting}

<!-- role: admin -->

| Problem | Check |
|---------|--------|
| Users see “Slack OAuth is not configured” | OAuth enabled + client ID/secret saved on **Slack integration** |
| `redirect_uri` mismatch | Redirect URL in Slack app must **exactly** match PowerHUB field (scheme, host, trailing slash) |
| `invalid_scope` | User scopes `chat:write`, `im:write` — not bot scopes only |
| Webhook test fails | URL correct, webhook enabled, channel not deleted |
| DMs not arriving | User connected Slack, master Slack on, event row enabled, not in quiet hours; check digest mode |
| Secrets after deploy | Re-enter if `SECRET_KEY` changed |

## Group chat channel sync {#chat-channel-sync}

<!-- role: admin -->

Mirror **Group Space** chat with mapped Slack channels (**two-way** when bot token and Events API are configured). Personal DMs (mentions / all messages) follow Notification settings unless channel sync is on for that space.

### 1. Slack app (bot)

1. Use the same Slack app or create one for PowerHUB.
2. **OAuth & Permissions → Bot Token Scopes**: add `chat:write`.
3. **Install to workspace** and copy the **Bot User OAuth Token** (`xoxb-…`).
4. Invite the bot to each channel you map (`/invite @YourBot`).

### 2. PowerHUB settings

1. **Administration → Slack integration**.
2. Enable **Group chat → Slack channel**, paste the **bot token**, and the **signing secret** (Events API) → **Save**.
3. Optional: **Send test bot message** with a channel ID (`C…`).

### 3. Map each chat

| Space type | Where to map |
|------------|----------------|
| Cohort group | **Administration → Cohorts & Groups** → edit group → Slack channel sync |
| Custom group space | **Administration → Group spaces** → space detail → Slack channel sync |

Enter the Slack **channel ID** (right-click channel → View channel details → copy ID at bottom).

### Behaviour

- New posts (text, links, snapshots) are queued to Slack asynchronously.
- Message includes author, space name, preview, and link back to PowerHUB.
- **Replies** in PowerHUB stay flat in chat (`↪ in reply to`) but post to the **Slack thread** when the parent is already synced.
- **Edits and deletes** sync both ways when channel sync is enabled.
- When channel sync is **on**, personal Slack DMs for mentions / all-messages are **skipped** — users see the channel post only. In-app and email notifications still follow user settings.
- When channel sync is **off**, personal mention / all-message Slack DMs work as before (Notification settings).
- **Two-way sync**: messages posted in a mapped Slack channel appear in PowerHUB when the author has connected Slack (Profile → Notification settings) with the same Slack user id.

### 4. Events API (Slack → PowerHUB)

1. In the Slack app: **Event Subscriptions** → enable → Request URL = the value shown on **Slack integration** (`…/accounts/slack/events/`).
2. Subscribe to bot events: **`message.channels`** (and `message.groups` / `message.im` if you use those channel types). Edits and deletes require the same `message.*` events — Slack delivers `message_changed` and `message_deleted` automatically.
3. Paste **Signing secret** on the Slack integration page (same app → Basic Information).
4. Users who post from Slack must **Connect Slack** on their PowerHUB profile so their `slack_user_id` can be matched.

Thread replies in Slack become separate chat rows with **↪ in reply to** linking the parent message.

## Field reference {#field-reference}

<!-- role: admin -->

| Field | Source |
|-------|--------|
| Enable personal Slack OAuth | Your policy — off in dev until ready |
| OAuth client ID | Slack app → Basic Information → Client ID |
| OAuth client secret | Slack app → Basic Information → Client Secret |
| OAuth redirect URI | `{SITE_URL}/accounts/slack/callback/` |
| Enable staff webhook | Your policy |
| Webhook URL | Slack app → Incoming Webhooks → channel URL |
| Enable chat channel sync | Your policy — requires bot token |
| Bot token | Slack app → OAuth & Permissions → Bot User OAuth Token (`xoxb-…`) |
| Signing secret | Slack app → Basic Information → Signing Secret |

`SITE_URL` must match how users reach PowerHUB (see `.env` / Render settings).
