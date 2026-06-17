## Profile {#profile}

Update **display name** and avatar — this is how others see you on the site (not your legal name).

- **Email** — login identifier; contact staff to change.
- **Password** — change via the password form; you may be forced to set a new password on first login.
- **Two-factor authentication** — manage TOTP via the Security section on your profile.
- **Privacy policy** — review what data Powercoders stores.

### Your data (GDPR / nDSG) {#privacy-data}

- **Export as Markdown** — downloads one `.md` file with all data linked to your account (journal, goals, tasks, workflows, reflections, habits, group posts, resources, feedback, notifications, and more).
- **Delete my account** — self-service erasure after password confirmation (permanent).

## Notification centre {#notifications}

The **notification centre** lists in-app alerts (bell icon or **Notification centre** on Profile). Opening the list marks items as read. Click an item to jump to the related page when a link is available.

Configure **how** you receive alerts on **Notification settings** (Profile → **Notification settings**).

## Notification settings {#notification-settings}

Control **in-app**, **email**, and **Slack** delivery per event type. Open **Notification settings** from Profile or use the ⓘ button on that page for this guide.

### Master switches

The **In-app**, **Email**, and **Slack** toggles in the table header turn an entire channel off. When a channel is off, the checkboxes in that column are greyed out and ignored until you turn the channel back on.

- **Slack** master switch stays disabled until you **Connect Slack** in the Slack connection card above the table.
- **Email** respects both the master switch here and your account’s email preference (kept in sync when you save).

### Event matrix

Each row is one kind of alert. Tick the channels you want for that event. What you see depends on your **role**:

| Role | Typical rows |
|------|----------------|
| **Student** | Feedback, new tasks/goals/workflows, deadline reminders, group chat mentions / all messages |
| **Teacher** | Student completed task/goal/workflow, reflection submitted, missed deadlines, group chat |
| **Admin** | Everything teachers see **plus** new bug reports, reopened reports, new user accounts |

Teachers are notified about students in **groups they teach**. Admins with student-activity alerts enabled receive those events for **all students** on the platform.

### Digest frequency

**Email and Slack delivery** can be **Instant**, **Hourly**, or **Daily**. Digest mode batches non-urgent email and Slack messages into one summary per hour or day.

- **In-app** alerts stay instant (unless you turn in-app off).
- **Deadline reminders** to students are always sent immediately on email/Slack, not held for a digest.

### Quiet hours and timezone

Set optional **quiet hours** and your **timezone**. During quiet hours, **email** and **Slack** are paused. In-app alerts are unaffected unless you disabled in-app.

Use the dropdowns to pick start/end times (30-minute steps) and your IANA timezone (e.g. Europe/Zurich).

### Slack connection

Connect your personal Slack workspace via OAuth to receive DMs. Use **Send test message** after connecting. Disconnect removes the link; Slack toggles cannot be enabled until you connect again.

### Group chat mentions

In group chat you can mention someone with `@"Display Name"` or `@email@example.com` (see Group Space help). Mention and “all messages” rows control those alerts separately.

### Unsaved changes

If you change settings and try to leave the page (another link, navbar, or closing the tab), PowerHUB warns you. You can **save and stay**, **save and leave**, or **discard changes**.

### For students {#notification-settings-students}

Focus on learning events: teacher feedback, assignments, deadlines, and group chat. You do not see teacher or admin oversight rows.

### For teachers {#notification-settings-teachers}

Use student-activity rows to follow submissions and overdue work in your groups without opening Student Progress for every check. Turn off rows you do not need to reduce noise; use digest mode for email/Slack if activity is high.

### For admins {#notification-settings-admins}

<!-- role: admin -->

You have **teacher-style** student-activity rows and **platform** rows (bug reports, reopened tickets, new accounts). Bug-report alerts replace the old “email every admin” behaviour — tune them here. New-user alerts fire when someone creates an account (UI or CSV import), except the creator is not notified about their own action.

Global reminder schedules (reflection nudges, deadline jobs) are configured under **Administration → Notification management**, not on this page.

## For students {#for-students}

Your cohort and group are assigned by staff; you cannot move yourself to another group on Profile.

## Staff: users and cohorts {#staff-management}

<!-- role: admin -->

| Role | In-app |
|------|--------|
| **Admin** | **Administration** menu: Cohorts & Groups, Student Progress, Users, import, File storage, Audit log. Full help: open ⓘ on any Administration page. |
| **Teacher** | **Student Progress** and **Student detail** for assigned groups; limited **Users** list. |

New users receive a **welcome email** (when mail is configured) and staff may get a **Slack** ping if `SLACK_WEBHOOK_URL` is set.

## Admin notes {#admin-only}

<!-- role: admin -->

- Prefer **Administration** in the top nav over Django admin for day-to-day user/cohort work (see ⓘ help on each tab).
- **Audit log** remains Django admin only.
- Register Celery Beat periodic task `accounts.tasks.notify_missing_reflections` for weekly missing-reflection Slack digests — see [TODO.md](../../../docs/plans/TODO.md).
