import logging

from django.db import IntegrityError
from django.utils import timezone

from accounts.models import Notification, NotificationDeliveryLog, UserNotificationSettings

from .constants import EVENT_SETTING_FIELD, EventType
from .settings import get_notification_settings

logger = logging.getLogger(__name__)


def event_enabled(settings, event_type):
    field_name = EVENT_SETTING_FIELD.get(event_type)
    if not field_name:
        return True
    return bool(getattr(settings, field_name, True))


def _claim_delivery(event_key, recipient, channel):
    if NotificationDeliveryLog.objects.filter(
        event_key=event_key,
        recipient=recipient,
        channel=channel,
    ).exists():
        return False, None
    try:
        log = NotificationDeliveryLog.objects.create(
            event_key=event_key,
            recipient=recipient,
            channel=channel,
            status=NotificationDeliveryLog.Status.QUEUED,
        )
        return True, log
    except IntegrityError:
        return False, None


def _finalize_delivery(log, *, status, error_message='', provider_message_id=''):
    log.status = status
    log.error_message = error_message
    log.provider_message_id = provider_message_id
    if status in (
        NotificationDeliveryLog.Status.SENT,
        NotificationDeliveryLog.Status.SKIPPED,
    ):
        log.sent_at = timezone.now()
    log.save(
        update_fields=[
            'status',
            'error_message',
            'provider_message_id',
            'sent_at',
        ],
    )


def _deliver_in_app(*, recipient, title, body, url):
    Notification.objects.create(
        recipient=recipient,
        title=title,
        body=body,
        url=url,
    )


def _deliver_email(*, recipient, subject, body):
    from accounts.emails import send_notification_email

    send_notification_email(recipient=recipient, subject=subject, body=body)


def dispatch_event(
    *,
    event_type,
    recipients,
    title,
    body='',
    url='',
    dedupe_key,
    email_subject=None,
    email_body=None,
    slack_text=None,
):
    """
    Route a notification to in-app (always when enabled), email, and Slack channels.

    Phase 0: in-app + email only. Slack deliveries are logged as skipped.
    """
    if not dedupe_key:
        raise ValueError('dedupe_key is required for dispatch_event')

    email_subject = email_subject or title
    email_body = email_body if email_body is not None else body

    for recipient in recipients:
        settings = get_notification_settings(recipient)
        if not event_enabled(settings, event_type):
            _log_skipped_all_channels(
                dedupe_key,
                recipient,
                reason=f'{event_type} disabled in user settings',
            )
            continue

        _dispatch_in_app(
            dedupe_key=dedupe_key,
            recipient=recipient,
            title=title,
            body=body,
            url=url,
        )

        if settings.email_enabled and recipient.email_notifications_enabled:
            _dispatch_email(
                dedupe_key=dedupe_key,
                recipient=recipient,
                subject=email_subject,
                body=email_body,
            )
        else:
            _log_skipped_channel(
                dedupe_key,
                recipient,
                NotificationDeliveryLog.Channel.EMAIL,
                reason='Email notifications disabled',
            )

        if settings.slack_enabled and slack_text:
            _dispatch_slack(
                dedupe_key=dedupe_key,
                recipient=recipient,
                text=slack_text,
            )
        elif slack_text:
            _log_skipped_channel(
                dedupe_key,
                recipient,
                NotificationDeliveryLog.Channel.SLACK,
                reason='Slack not enabled for user',
            )


def _dispatch_in_app(*, dedupe_key, recipient, title, body, url):
    channel = NotificationDeliveryLog.Channel.IN_APP
    claimed, log = _claim_delivery(dedupe_key, recipient, channel)
    if not claimed:
        return
    try:
        _deliver_in_app(recipient=recipient, title=title, body=body, url=url)
        _finalize_delivery(log, status=NotificationDeliveryLog.Status.SENT)
    except Exception as exc:
        logger.warning('In-app notification failed for user %s', recipient.pk, exc_info=True)
        _finalize_delivery(
            log,
            status=NotificationDeliveryLog.Status.FAILED,
            error_message=str(exc),
        )


def _dispatch_email(*, dedupe_key, recipient, subject, body):
    channel = NotificationDeliveryLog.Channel.EMAIL
    claimed, log = _claim_delivery(dedupe_key, recipient, channel)
    if not claimed:
        return
    try:
        _deliver_email(recipient=recipient, subject=subject, body=body)
        _finalize_delivery(log, status=NotificationDeliveryLog.Status.SENT)
    except Exception as exc:
        logger.warning('Email notification failed for user %s', recipient.pk, exc_info=True)
        _finalize_delivery(
            log,
            status=NotificationDeliveryLog.Status.FAILED,
            error_message=str(exc),
        )


def _dispatch_slack(*, dedupe_key, recipient, text):
    from accounts.models import SlackIntegration

    channel = NotificationDeliveryLog.Channel.SLACK
    claimed, log = _claim_delivery(dedupe_key, recipient, channel)
    if not claimed:
        return

    settings = get_notification_settings(recipient)
    if not settings.slack_enabled:
        _finalize_delivery(
            log,
            status=NotificationDeliveryLog.Status.SKIPPED,
            error_message='Slack notifications disabled in user settings',
        )
        return

    try:
        integration = recipient.slack_integration
    except SlackIntegration.DoesNotExist:
        integration = None

    if not integration or not integration.is_connected:
        _finalize_delivery(
            log,
            status=NotificationDeliveryLog.Status.SKIPPED,
            error_message='Slack not connected',
        )
        return

    try:
        from accounts.slack_provider import send_user_dm

        message_id = send_user_dm(
            access_token=integration.get_access_token(),
            slack_user_id=integration.slack_user_id,
            text=text,
        )
        integration.last_error = ''
        integration.save(update_fields=['last_error'])
        _finalize_delivery(
            log,
            status=NotificationDeliveryLog.Status.SENT,
            provider_message_id=message_id,
        )
    except Exception as exc:
        logger.warning('Slack notification failed for user %s', recipient.pk, exc_info=True)
        if integration:
            integration.last_error = str(exc)[:500]
            integration.save(update_fields=['last_error'])
        _finalize_delivery(
            log,
            status=NotificationDeliveryLog.Status.FAILED,
            error_message=str(exc),
        )


def _log_skipped_channel(dedupe_key, recipient, channel, *, reason):
    claimed, log = _claim_delivery(dedupe_key, recipient, channel)
    if not claimed:
        return
    _finalize_delivery(
        log,
        status=NotificationDeliveryLog.Status.SKIPPED,
        error_message=reason,
    )


def _log_skipped_all_channels(dedupe_key, recipient, *, reason):
    for channel in NotificationDeliveryLog.Channel:
        _log_skipped_channel(dedupe_key, recipient, channel, reason=reason)
