# Slack Integration Implementation Plan

## Goal

Implement personal Slack integration for PowerHUB so each user can connect their Slack account, receive notifications relevant to them based on personal settings, and optionally sync group chat with Slack.

## Scope

Two Slack communication streams:

1. `PowerHUB Notifications` (personal notifications, DM-style)
2. `Group Chat` (group-level channel sync)

This plan is aligned with the current architecture:

- Django monolith
- `accounts.Notification` for in-app notifications
- Celery for async jobs/reminders
- `group_space` as the app chat source
- Existing global webhook utility in `accounts/slack.py`

---

## Current State (As-Is)

- Slack currently supports only one global outgoing webhook (`SLACK_WEBHOOK_URL`).
- No per-user Slack OAuth connection.
- Notifications are partially centralized (`accounts.emails.notify_feedback_received`).
- Group chat exists and is flat timeline (`group_space` app), no thread model.
- Celery is available for background delivery and scheduling.

---

## Target State (To-Be)

### Personal Slack

- Each user can connect/disconnect Slack via OAuth.
- Per-user notification settings decide what is sent to Slack.
- Delivery is async via Celery.
- In-app notifications remain the source of truth and continue to work regardless of Slack state.

### Group Chat Slack Sync

- Sync between PowerHUB group chat and a mapped Slack channel.
- Thread replies from Slack are represented in PowerHUB flat chat via a reply-reference line:
  - `↪ in reply to: "<first words>" by <user>`
  - Click navigates to the original post.

---

## Product Decisions

1. **Disconnect behavior**
   - Stop future Slack deliveries immediately.
   - Keep historical Slack messages (no retroactive deletion).
   - Keep in-app notifications active.

2. **Separate toggles**
   - Personal notifications toggle.
   - Group chat sync toggle.

3. **Thread mapping policy**
   - Keep PowerHUB flat structure.
   - Render lightweight reply context with link to root post.

4. **Initial sync direction**
   - Start with one-way group sync (PowerHUB -> Slack).
   - Add two-way sync (Slack -> PowerHUB) in a later phase.

---

## Data Model Changes

## 1) User Slack connection

Add model: `SlackIntegration` (1:1 with `accounts.User`)

Suggested fields:

- `user` (OneToOne)
- `is_active` (bool)
- `slack_user_id` (string)
- `slack_team_id` (string)
- `access_token_encrypted` (text, encrypted at rest)
- `refresh_token_encrypted` (optional)
- `token_expires_at` (optional datetime)
- `connected_at` (datetime)
- `disconnected_at` (nullable datetime)
- `last_error` (nullable text)

Indexes:

- unique on (`slack_team_id`, `slack_user_id`)

## 2) Notification preferences

Add model: `UserNotificationSettings` (1:1 with `accounts.User`)

Suggested fields:

- `slack_enabled`
- `email_enabled` (future-proof, optional)
- `notify_new_workflow`
- `notify_new_task`
- `notify_new_goal`
- `notify_feedback`
- `notify_deadline_reminder`
- `notify_group_chat_mentions`
- `notify_group_chat_all_messages`
- `digest_mode` (`instant`, `hourly`, `daily`)
- `quiet_hours_start`
- `quiet_hours_end`
- `timezone`

## 3) Delivery log / idempotency

Add model: `NotificationDeliveryLog`

Suggested fields:

- `event_key` (idempotency key)
- `recipient` (FK user)
- `channel` (`in_app`, `email`, `slack`)
- `status` (`queued`, `sent`, `failed`, `skipped`)
- `provider_message_id` (nullable)
- `error_message` (nullable)
- `created_at`, `sent_at`

Constraint:

- unique(`event_key`, `recipient`, `channel`)

## 4) Group chat sync mapping

Extend `group_space.Post` (or add dedicated mapping model) with:

- `source_system` (`powerhub`, `slack`)
- `slack_channel_id` (nullable)
- `slack_ts` (nullable)
- `slack_thread_ts` (nullable)
- `reply_to_post` (nullable FK -> `Post`)

Constraint:

- unique(`slack_channel_id`, `slack_ts`) for idempotent upsert

---

## Backend Architecture

## 1) Unified dispatcher service

Create new module, for example:

- `backend/accounts/notifications/dispatcher.py`

Core API:

- `dispatch_event(event_type, actor, recipients, payload, url, dedupe_key)`

Responsibilities:

- Creates in-app `Notification`.
- Reads per-user settings.
- Enqueues Slack/email sends.
- Writes delivery logs.
- Applies dedupe and quiet-hours rules.

## 2) Slack provider service

Create:

- `backend/accounts/slack_provider.py`

Responsibilities:

- OAuth token exchange/refresh
- send DM or channel message
- structured error handling (rate limits, invalid_auth, revoked token)
- standardized response object

## 3) Celery tasks

Create tasks:

- `send_slack_notification_task`
- `send_slack_group_message_task`
- `run_deadline_reminders_task`
- `run_digest_task` (if digest enabled)

Rules:

- Re-check user settings at execution time.
- Retries with exponential backoff.
- Skip safely when disconnected.

---

## API and Views

In `accounts`:

- `GET /accounts/slack/connect/` -> start OAuth
- `GET /accounts/slack/callback/` -> finalize connection
- `POST /accounts/slack/disconnect/`
- `POST /accounts/slack/test-message/`

Settings endpoints/pages:

- `GET /accounts/notifications/settings/`
- `POST /accounts/notifications/settings/`

For group sync admin/config:

- mapping UI for `Group` <-> Slack channel id
- sync on/off per group

---

## Event Coverage (What triggers notifications)

Phase 1 (MVP):

- feedback received
- new workflow assigned/published to relevant student(s)
- new task assigned
- new goal assigned

Phase 2:

- deadline reminders (24h, 2h, overdue)
- mention in group chat
- optional all group chat messages

Phase 3:

- two-way group chat sync
- edited/deleted message synchronization

---

## Thread to Flat Mapping (Slack -> PowerHUB)

Rules:

1. Slack top-level message -> regular `Post`.
2. Slack thread reply -> regular `Post` with `reply_to_post`.
3. UI adds reference line:
   - `↪ in reply to: "<preview>" by <author>`
4. Click on reference navigates to original post anchor.

Out-of-order handling:

- if root message not found yet, store pending mapping by (`channel`, `thread_ts`)
- retry reconcile job periodically

Fallback:

- if root unavailable or inaccessible, show:
  - `↪ in reply to an unavailable message`

---

## Rollout Plan

## Phase 0 - Foundation

- Add models + migrations
- Add settings UI skeleton
- Introduce dispatcher abstraction (in-app path only)
- Add delivery logs

## Phase 1 - Personal Slack MVP

- OAuth connect/disconnect/test
- Slack DM sending
- Integrate dispatcher with feedback + assigned entities
- Add per-user toggles and enforce them

## Phase 2 - Reminders and reliability

- deadline reminder scheduler
- quiet hours + timezone support
- digest mode
- retries and monitoring dashboards/logging

## Phase 3 - Group sync

- one-way PowerHUB -> Slack channel sync
- channel mapping UI
- mute per-user for group channel relays

## Phase 4 - Two-way sync

- Slack Events API endpoint
- verify signatures
- idempotent ingest
- thread-to-flat mapping with reply links

---

## Security and Compliance

- Encrypt Slack tokens at rest.
- Never log raw access tokens.
- Validate Slack request signatures and timestamp.
- Apply permission checks before sending object-related content.
- Respect privacy visibility rules from existing domain apps.
- Add account-level disconnect and token revocation flow.

---

## Testing Strategy

Unit tests:

- settings filtering logic
- dispatcher channel routing
- dedupe behavior
- thread mapping resolver

Integration tests:

- OAuth callback flow
- disconnect behavior (deliveries stop)
- reminder task behavior with enabled/disabled flags
- group sync create/update/delete events

Regression tests:

- existing in-app notifications remain intact
- performance impact on chat posting is minimal (async offload)

Manual QA scenarios:

- user connects Slack and receives test DM
- user disables Slack and no further Slack sends happen
- user keeps in-app notifications after disconnect
- thread reply shows correct "in reply to" reference and navigation

---

## Definition of Done (MVP)

MVP is complete when:

- User can connect/disconnect Slack from settings.
- User can control Slack notifications with switches.
- Relevant events produce in-app notifications and optional Slack DM.
- Disconnect stops future Slack sends without affecting in-app notifications.
- Delivery logs exist for support/debugging.

---

## Open Questions

1. One Slack workspace only, or multi-workspace support per deployment?
2. Is `Group Chat` sync channel-level or user-level for posting permissions?
3. Should group sync include files immediately or text/links first?
4. Do we require message editing/deletion sync in MVP?
5. What are anti-spam defaults for very active groups?

---

## Recommended Next Step

Start with Phase 0 + Phase 1 in one implementation slice:

1. `SlackIntegration`
2. `UserNotificationSettings`
3. Dispatcher abstraction
4. OAuth connect/disconnect/test
5. Feedback event Slack DM through dispatcher

This delivers value quickly while creating a stable base for reminders and group sync.
