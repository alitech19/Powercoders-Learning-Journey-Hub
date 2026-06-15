## Profile {#profile}

Update **display name** and avatar — this is how others see you on the site (not your legal name).

- **Email** — login identifier; contact staff to change.
- **Password** — change via the password form; you may be forced to set a new password on first login.
- **Email notifications** — toggle whether the platform may email you when teachers leave feedback.
- **Two-factor authentication** — manage TOTP via the Security section on your profile.
- **Privacy policy** — review what data Powercoders stores.

### Your data (GDPR / nDSG) {#privacy-data}

- **Export as Markdown** — downloads one `.md` file with all data linked to your account (journal, goals, tasks, workflows, reflections, habits, group posts, resources, feedback, notifications, and more).
- **Delete my account** — self-service erasure after password confirmation (permanent).

## Notifications {#notifications}

The **notification centre** (bell in the top bar) lists in-app alerts — for example when a teacher leaves feedback. Opening the list marks items as read. Email copies respect your **Email notifications** toggle on Profile.

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
