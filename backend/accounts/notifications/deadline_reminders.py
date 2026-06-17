from datetime import timedelta

from django.utils import timezone

from accounts.notifications.constants import EventType
from accounts.notifications.dispatcher import dispatch_event
from accounts.notifications.staff_events import notify_student_deadline_overdue


def _task_is_complete(enrollment):
    from tasks.models import Task

    return enrollment.status == Task.Status.DONE


def _goal_is_complete(enrollment):
    from goals.models import GoalEnrollment

    return enrollment.status in (GoalEnrollment.Status.COMPLETED, GoalEnrollment.Status.ABANDONED)


def _build_message(label, title):
    if label == '24h':
        return f"Deadline reminder: '{title}' is due in about 24 hours."
    if label == '2h':
        return f"Deadline reminder: '{title}' is due today (about 2 hours left)."
    return f"Overdue: '{title}' deadline has passed."


def send_deadline_reminders(config=None):
    from goals.models import GoalEnrollment
    from tasks.models import TaskEnrollment

    today = timezone.localdate()

    for enrollment in TaskEnrollment.objects.select_related('task', 'student'):
        due = enrollment.task.due_date
        if not due or _task_is_complete(enrollment):
            continue
        _dispatch_for_enrollment(
            kind='task',
            item_id=enrollment.task_id,
            user=enrollment.student,
            title=enrollment.task.title,
            due_date=due,
            detail_url=f'/tasks/{enrollment.task_id}/',
            today=today,
            config=config,
        )

    for enrollment in GoalEnrollment.objects.select_related('goal', 'student'):
        due = enrollment.goal.target_date
        if not due or _goal_is_complete(enrollment):
            continue
        _dispatch_for_enrollment(
            kind='goal',
            item_id=enrollment.goal_id,
            user=enrollment.student,
            title=enrollment.goal.title,
            due_date=due,
            detail_url=f'/goals/{enrollment.goal_id}/',
            today=today,
            config=config,
        )


def _dispatch_for_enrollment(*, kind, item_id, user, title, due_date, detail_url, today, config=None):
    if due_date < today:
        label = 'overdue'
        dedupe_day = today.isoformat()
        if config and not config.reminder_offset_overdue:
            return
    elif due_date == today:
        label = '2h'
        dedupe_day = due_date.isoformat()
        if config and not config.reminder_offset_2h:
            return
    elif due_date == today + timedelta(days=1):
        label = '24h'
        dedupe_day = due_date.isoformat()
        if config and not config.reminder_offset_24h:
            return
    else:
        return

    body = _build_message(label, title)
    dispatch_event(
        event_type=EventType.DEADLINE_REMINDER,
        recipients=[user],
        title=f'Deadline reminder: {title}',
        body=body,
        url=detail_url,
        dedupe_key=f'deadline:{kind}:{item_id}:{user.pk}:{label}:{dedupe_day}',
        email_subject=f'PowerHUB deadline reminder: {title}',
        email_body=f'Hi {user.display_name},\n\n{body}\n\n— Powercoders Team',
        slack_text=f'⏰ {body}',
    )
    if label == 'overdue':
        notify_student_deadline_overdue(
            student=user,
            kind=kind,
            item_id=item_id,
            title=title,
            detail_url=detail_url,
            dedupe_day=dedupe_day,
        )
