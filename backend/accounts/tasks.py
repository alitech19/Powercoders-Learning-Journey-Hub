from celery import shared_task
from zoneinfo import ZoneInfo

from django.utils import timezone


@shared_task
def notify_task_assigned_task(task_id, student_ids, actor_id):
    from accounts.models import User
    from accounts.notifications.entity_events import notify_task_assigned
    from tasks.models import Task

    task = Task.objects.get(pk=task_id)
    students = User.objects.filter(pk__in=student_ids, role=User.Role.STUDENT, is_active=True)
    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    notify_task_assigned(task=task, students=students, actor=actor)


@shared_task
def notify_goal_assigned_task(goal_id, student_ids, actor_id):
    from accounts.models import User
    from accounts.notifications.entity_events import notify_goal_assigned
    from goals.models import Goal

    goal = Goal.objects.get(pk=goal_id)
    students = User.objects.filter(pk__in=student_ids, role=User.Role.STUDENT, is_active=True)
    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    notify_goal_assigned(goal=goal, students=students, actor=actor)


@shared_task
def notify_workflow_assigned_task(workflow_id, student_ids, actor_id):
    from accounts.models import User
    from accounts.notifications.entity_events import notify_workflow_assigned
    from workflows.models import Workflow

    workflow = Workflow.objects.get(pk=workflow_id)
    students = User.objects.filter(pk__in=student_ids, role=User.Role.STUDENT, is_active=True)
    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    notify_workflow_assigned(workflow=workflow, students=students, actor=actor)


@shared_task
def run_deadline_reminders_task():
    from accounts.notifications.deadline_reminders import send_deadline_reminders
    from config.models import NotificationConfig

    config = NotificationConfig.get()
    if not config.deadline_reminders_enabled:
        return
    try:
        send_deadline_reminders(config=config)
        config.record_run()
    except Exception as exc:
        config.record_run(error=str(exc))
        raise


@shared_task
def notify_missing_reflections():
    """Slack digest: students without a weekly reflection submitted this week."""
    from config.models import NotificationConfig

    config = NotificationConfig.get()
    if not config.reflection_digest_enabled:
        return

    from django.contrib.auth import get_user_model

    from dashboard.services import students_missing_weekly_reflection

    from .slack import send_slack_message

    User = get_user_model()
    students = list(
        User.objects.filter(role=User.Role.STUDENT, is_active=True).select_related('group')
    )
    missing = students_missing_weekly_reflection(students)
    if not missing:
        send_slack_message("✅ All students have submitted this week's reflection.")
        return

    count = len(missing)
    lines = '\n'.join(
        f'• {s.display_name} ({s.group.name if s.group else "no group"})' for s in missing
    )
    send_slack_message(
        f"⚠️ *{count} student{'s' if count != 1 else ''} missing this week's reflection:*\n{lines}"
    )


def _bucket_boundary(*, bucket: str):
    """Return timezone-aware bucket boundary in Europe/Zurich."""
    tz = ZoneInfo('Europe/Zurich')
    now_local = timezone.now().astimezone(tz)
    if bucket == 'hourly':
        return now_local.replace(minute=0, second=0, microsecond=0)
    return now_local.replace(hour=0, minute=0, second=0, microsecond=0)


def _dispatch_notification_digests(*, bucket: str):
    from accounts.emails import send_notification_email
    from accounts.models import NotificationDigestItem, NotificationDeliveryLog
    from accounts.notifications.dispatcher import in_quiet_hours
    from accounts.notifications.settings import get_notification_settings
    from accounts.slack_provider import send_user_dm, SlackApiError
    from accounts.models import SlackIntegration

    boundary = _bucket_boundary(bucket=bucket)

    items_qs = (
        NotificationDigestItem.objects.select_related('recipient')
        .filter(digest_bucket=bucket, scheduled_for=boundary, status=NotificationDigestItem.Status.QUEUED)
        .order_by('created_at')
    )
    if not items_qs.exists():
        return  # nothing to do

    # Group by (recipient, channel).
    grouped: dict[tuple[int, str], list[NotificationDigestItem]] = {}
    for item in items_qs:
        grouped.setdefault((item.recipient_id, item.channel), []).append(item)

    for (recipient_id, channel), items in grouped.items():
        recipient = items[0].recipient
        settings = get_notification_settings(recipient)

        if in_quiet_hours(settings):
            # Skip delivery for the whole bucket.
            NotificationDigestItem.objects.filter(
                recipient_id=recipient_id,
                channel=channel,
                digest_bucket=bucket,
                scheduled_for=boundary,
                status=NotificationDigestItem.Status.QUEUED,
            ).update(status=NotificationDigestItem.Status.SKIPPED, sent_at=timezone.now())
            NotificationDeliveryLog.objects.filter(
                recipient_id=recipient_id,
                channel=(
                    NotificationDeliveryLog.Channel.EMAIL
                    if channel == NotificationDigestItem.Channel.EMAIL
                    else NotificationDeliveryLog.Channel.SLACK
                ),
                event_key__in=[i.event_key for i in items],
                status=NotificationDeliveryLog.Status.QUEUED,
            ).update(
                status=NotificationDeliveryLog.Status.SKIPPED,
                error_message='In quiet hours',
                sent_at=timezone.now(),
            )
            continue

        event_keys = [i.event_key for i in items]

        if channel == NotificationDigestItem.Channel.EMAIL:
            if not (settings.email_enabled and recipient.email_notifications_enabled):
                NotificationDigestItem.objects.filter(
                    recipient_id=recipient_id,
                    channel=channel,
                    digest_bucket=bucket,
                    scheduled_for=boundary,
                    status=NotificationDigestItem.Status.QUEUED,
                ).update(status=NotificationDigestItem.Status.SKIPPED, sent_at=timezone.now())
                NotificationDeliveryLog.objects.filter(
                    recipient_id=recipient_id,
                    channel=NotificationDeliveryLog.Channel.EMAIL,
                    event_key__in=event_keys,
                    status=NotificationDeliveryLog.Status.QUEUED,
                ).update(
                    status=NotificationDeliveryLog.Status.SKIPPED,
                    error_message='Email notifications disabled',
                    sent_at=timezone.now(),
                )
                continue

            subject = f'You have {len(items)} new notification{"s" if len(items) != 1 else ""}'
            lines = []
            for i in items:
                lines.append(f'• {i.title}')
                if i.email_body:
                    lines.append(i.email_body.strip())
                if i.url:
                    lines.append(f'Link: {i.url}')
                lines.append('')
            body = f'Hi {recipient.display_name},\n\n' + '\n'.join(lines)

            try:
                send_notification_email(recipient=recipient, subject=subject, body=body)
                sent_at = timezone.now()
                NotificationDigestItem.objects.filter(
                    recipient_id=recipient_id,
                    channel=channel,
                    digest_bucket=bucket,
                    scheduled_for=boundary,
                    status=NotificationDigestItem.Status.QUEUED,
                ).update(status=NotificationDigestItem.Status.SENT, sent_at=sent_at)
                NotificationDeliveryLog.objects.filter(
                    recipient_id=recipient_id,
                    channel=NotificationDeliveryLog.Channel.EMAIL,
                    event_key__in=event_keys,
                    status=NotificationDeliveryLog.Status.QUEUED,
                ).update(status=NotificationDeliveryLog.Status.SENT, sent_at=sent_at, error_message='', provider_message_id='')
            except Exception as exc:
                err = str(exc)[:2000]
                sent_at = timezone.now()
                NotificationDigestItem.objects.filter(
                    recipient_id=recipient_id,
                    channel=channel,
                    digest_bucket=bucket,
                    scheduled_for=boundary,
                    status=NotificationDigestItem.Status.QUEUED,
                ).update(status=NotificationDigestItem.Status.FAILED, sent_at=sent_at, error_message=err)
                NotificationDeliveryLog.objects.filter(
                    recipient_id=recipient_id,
                    channel=NotificationDeliveryLog.Channel.EMAIL,
                    event_key__in=event_keys,
                    status=NotificationDeliveryLog.Status.QUEUED,
                ).update(status=NotificationDeliveryLog.Status.FAILED, sent_at=sent_at, error_message=err)

        else:
            # Slack digest
            integration = None
            try:
                integration = recipient.slack_integration
            except SlackIntegration.DoesNotExist:
                integration = None

            if not (settings.slack_enabled and integration and integration.is_connected):
                NotificationDigestItem.objects.filter(
                    recipient_id=recipient_id,
                    channel=channel,
                    digest_bucket=bucket,
                    scheduled_for=boundary,
                    status=NotificationDigestItem.Status.QUEUED,
                ).update(status=NotificationDigestItem.Status.SKIPPED, sent_at=timezone.now())
                NotificationDeliveryLog.objects.filter(
                    recipient_id=recipient_id,
                    channel=NotificationDeliveryLog.Channel.SLACK,
                    event_key__in=event_keys,
                    status=NotificationDeliveryLog.Status.QUEUED,
                ).update(
                    status=NotificationDeliveryLog.Status.SKIPPED,
                    error_message='Slack not connected',
                    sent_at=timezone.now(),
                )
                continue

            slack_lines = []
            for i in items:
                slack_lines.append(f'• {i.title}')
                if i.slack_text:
                    slack_lines.append(i.slack_text.strip())
                if i.url:
                    slack_lines.append(i.url)
                slack_lines.append('')
            text = '\n'.join(slack_lines).strip()

            try:
                message_id = send_user_dm(
                    access_token=integration.get_access_token(),
                    slack_user_id=integration.slack_user_id,
                    text=text,
                )
                integration.last_error = ''
                integration.save(update_fields=['last_error'])
                sent_at = timezone.now()
                NotificationDigestItem.objects.filter(
                    recipient_id=recipient_id,
                    channel=channel,
                    digest_bucket=bucket,
                    scheduled_for=boundary,
                    status=NotificationDigestItem.Status.QUEUED,
                ).update(status=NotificationDigestItem.Status.SENT, sent_at=sent_at, provider_message_id=message_id, error_message='')
                NotificationDeliveryLog.objects.filter(
                    recipient_id=recipient_id,
                    channel=NotificationDeliveryLog.Channel.SLACK,
                    event_key__in=event_keys,
                    status=NotificationDeliveryLog.Status.QUEUED,
                ).update(status=NotificationDeliveryLog.Status.SENT, sent_at=sent_at, provider_message_id=message_id, error_message='')
            except SlackApiError as exc:
                err = str(exc)[:2000]
                sent_at = timezone.now()
                integration.last_error = err[:500]
                integration.save(update_fields=['last_error'])
                NotificationDigestItem.objects.filter(
                    recipient_id=recipient_id,
                    channel=channel,
                    digest_bucket=bucket,
                    scheduled_for=boundary,
                    status=NotificationDigestItem.Status.QUEUED,
                ).update(status=NotificationDigestItem.Status.FAILED, sent_at=sent_at, error_message=err)
                NotificationDeliveryLog.objects.filter(
                    recipient_id=recipient_id,
                    channel=NotificationDeliveryLog.Channel.SLACK,
                    event_key__in=event_keys,
                    status=NotificationDeliveryLog.Status.QUEUED,
                ).update(status=NotificationDeliveryLog.Status.FAILED, sent_at=sent_at, error_message=err)


@shared_task
def dispatch_hourly_notification_digests_task():
    _dispatch_notification_digests(bucket='hourly')


@shared_task
def dispatch_daily_notification_digests_task():
    _dispatch_notification_digests(bucket='daily')
