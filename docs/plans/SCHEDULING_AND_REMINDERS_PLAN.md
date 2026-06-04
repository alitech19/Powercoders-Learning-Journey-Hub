# Scheduling and Reminders Plan

## Goal

Implement scheduling capabilities for learning activities and notifications:

1. Scheduled publish for existing entities (`Task`, `Goal`, `Workflow`, and future entities)
2. Deadline reminders for entity-related activities
3. Standalone reminders (one-time and recurring) created by staff

All time logic is based on **Europe/Zurich**.

---

## Product Scope (Agreed)

## 1) Scheduled publish (entity-based)

- Add `publish_at` to supported entities.
- Published behavior must remain consistent with each entity's existing visibility rules.
- Before `publish_at`, content stays hidden from target users.
- At `publish_at`, content becomes visible automatically.
- If entity is changed or removed, scheduled publish must be updated or canceled.

## 2) Deadline reminders (entity-based)

- Reminders can be configured relative to entity deadline (e.g., 24h, 2h, overdue).
- Send only to relevant users (assigned/enrolled and not yet completed when applicable).
- Respect notification channel settings (in-app required baseline; email/Slack optional by user settings).

## 3) Standalone reminders (not tied to entities)

- Staff can create reminder campaigns for general communication.
- Supported modes:
  - one-time
  - recurring (daily/weekly/monthly)
- Targeting options:
  - cohort
  - group
  - selected users
  - role-based set (optional future extension)

---

## Validation Rules

For entity forms (create/edit):

- `publish_at` must not be after `deadline_at`.
- Reminder trigger times must not be after `deadline_at`.
- Invalid schedule combinations block save with clear inline errors.

On entity edit:

- Recompute future reminders when deadline/schedule fields change.
- Cancel no-longer-valid pending jobs.
- Keep sent reminders in history (audit only, no rollback).

On entity delete/archive/deactivate:

- Cancel all pending scheduled actions tied to that entity.

---

## Delivery and Rate Strategy

Delivery constraints:

- Global send pace target: **1 scheduler batch per minute**.
- One batch may include multiple messages.
- Apply random second jitter inside minute buckets to avoid spikes at `HH:00:00`.

Operational behavior:

- Idempotent delivery keys to avoid duplicates.
- Retry failed sends with bounded backoff.
- Re-check settings/permissions at send time (not only schedule time).

---

## UI Placement Plan

## 1) User-level settings (notification preferences)

Location:

- `accounts/profile/` -> `Notifications & Integrations` section

Content:

- channel toggles (in-app/email/Slack)
- event-type toggles (new task/goal/workflow, feedback, reminders, group chat)
- quiet hours (future)

## 2) Entity scheduling controls

Locations:

- task create/edit
- goal create/edit
- workflow create/edit

UI block:

- `Schedule` section with:
  - `Publish at` (Zurich time)
  - reminder presets + optional custom reminder points
  - inline validation errors

## 3) Standalone reminders management (staff-only)

New area:

- Navigation entry: `Automation` or `Reminders`
- Candidate route: `/notifications/reminders/`

Views:

- list of campaigns (status, target, next run)
- create/edit campaign
- pause/resume/archive actions
- run history and delivery outcomes

## 4) Observability in existing pages

- Entity detail pages:
  - `Scheduled publish`
  - `Next reminder`
  - `Last reminder sent`
- Staff dashboard widget:
  - `Today's scheduled actions`
  - `Failed deliveries`

---

## Proposed Data Model

## A) Generic scheduler primitives

`ScheduledAction`

- `action_type` (`publish_entity`, `entity_deadline_reminder`, `standalone_reminder`)
- `target_content_type`, `target_object_id` (nullable for standalone)
- `execute_at` (Zurich-normalized, stored timezone-aware)
- `status` (`pending`, `processing`, `sent`, `failed`, `canceled`)
- `payload` (JSON)
- `dedupe_key`
- `created_by` (nullable staff user)
- timestamps

Constraint:

- unique on `dedupe_key`

`ScheduledActionDelivery`

- `scheduled_action`
- `recipient`
- `channel` (`in_app`, `email`, `slack`)
- `status` (`queued`, `sent`, `failed`, `skipped`)
- `provider_id` (nullable)
- `error` (nullable)
- timestamps

## B) Standalone campaign model

`ReminderCampaign`

- `title`
- `message`
- `link` (optional)
- `status` (`draft`, `active`, `paused`, `archived`, `completed`)
- `schedule_type` (`once`, `daily`, `weekly`, `monthly`)
- schedule params (time/day rules)
- target scope fields (cohort/group/users)
- `timezone` (fixed default `Europe/Zurich`)
- `created_by`
- timestamps

`ReminderCampaignRun`

- `campaign`
- `planned_at`
- `started_at`, `finished_at`
- `status`
- counters (sent/failed/skipped)

---

## Architecture and Processing Flow

## 1) Scheduler engine

- Beat-triggered coordinator runs every minute.
- Picks due `ScheduledAction` rows (`pending`, `execute_at <= now`).
- Locks rows for processing.
- Enqueues delivery tasks in batches.

## 2) Delivery dispatcher

- Central dispatcher decides channels per recipient.
- Applies user settings.
- Applies permissions and visibility checks.
- Writes in-app notification as baseline event artifact.

## 3) Jitter strategy

- For large recipient sets, split into minute bucket batch.
- Add random seconds offset (`0..59`) per recipient/job item.
- Maintain deterministic dedupe key independent of jitter.

---

## Scenarios (Examples)

## Entity-based

1. Teacher schedules task publish for Monday 09:00.
2. Students see task at 09:00 Zurich.
3. Deadline reminders send at configured offsets.
4. Teacher edits deadline from Friday to Thursday.
5. Future reminder schedule recalculates; invalid old reminders cancel.

## Standalone one-time

1. Staff creates "Bring your laptop tomorrow" reminder for Group A at 18:00.
2. Campaign activates and run is generated.
3. Recipients receive messages based on their channel preferences.

## Standalone recurring

1. Staff creates weekly reminder every Sunday 19:00 for Cohort X.
2. System creates next run at each cycle.
3. Staff pauses campaign during holidays, then resumes.

---

## Permissions and Safety

- Only staff (teacher/admin) can create/edit campaigns.
- Teacher scope should be limited to assigned groups where required by existing permission model.
- Prevent sending reminders for inaccessible targets.
- Keep immutable audit trail for sent/canceled/failed actions.

---

## Rollout Plan

## Phase 1: Foundation

- Add scheduler primitives (`ScheduledAction`, delivery log).
- Integrate dispatcher with in-app notifications.
- Add dashboard operational visibility for scheduled jobs.

## Phase 2: Entity scheduling MVP

- Add `publish_at` + reminder config fields to task/goal/workflow forms.
- Validation rules and cancellation/update logic on edit/delete.
- Deliver in-app reminders first, then optional email/Slack.

## Phase 3: Standalone reminders MVP

- Add `ReminderCampaign` CRUD for staff.
- One-time reminders and weekly recurrence first.
- Add pause/resume/archive.

## Phase 4: Reliability and scale

- Batch send pacing, jitter, and stronger retry policy.
- Enhanced reporting (per campaign, per channel success rates).
- Expand recurrence patterns and template library.

---

## Acceptance Criteria (MVP)

1. Staff can schedule `publish_at` for task/goal/workflow.
2. System prevents schedule values after deadline.
3. Editing deadline updates or cancels related pending reminders.
4. Deleting/archiving entity cancels pending jobs.
5. Staff can create one-time and recurring standalone reminders.
6. Reminders respect user channel preferences.
7. Scheduler sends in controlled batches with jitter and no duplicate sends.
8. Admin/staff can inspect delivery outcomes.

---

## Non-Goals (Initial)

- Per-user timezone scheduling (all Zurich for now)
- Advanced recurrence editor (RRULE-level complexity)
- Immediate two-way chat automation logic in this scope

---

## Open Decisions

1. Final naming in UI: `Automation` vs `Reminders`.
2. Which recurrence options ship in MVP (weekly-only vs daily+weekly).
3. Whether `overdue` reminders are single-shot or repeated until completion.
4. Max batch size per minute for each channel provider.

---

## Recommended Next Step

Start with Phase 1 + Phase 2 for one entity (Task) as pilot:

1. scheduler primitives
2. task `publish_at` and reminder validation
3. end-to-end send path with logs
4. expand same pattern to Goal and Workflow

This minimizes risk while validating UX and operations before full rollout.
