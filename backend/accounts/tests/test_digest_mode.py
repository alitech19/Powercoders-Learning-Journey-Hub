from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from accounts.models import NotificationDigestItem, NotificationDeliveryLog, SlackIntegration
from accounts.notifications.constants import EventType
from accounts.notifications.dispatcher import dispatch_event
from accounts.notifications.settings import get_notification_settings
from accounts.tasks import dispatch_hourly_notification_digests_task
from test_utils.users import make_student

from django.utils import timezone
from zoneinfo import ZoneInfo


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class DigestModeEmailTests(TestCase):
    def test_hourly_email_queues_and_dispatches(self):
        student = make_student('digest-email@example.com', email_notifications_enabled=True)
        settings = get_notification_settings(student)
        settings.digest_mode = settings.DigestMode.HOURLY
        settings.email_feedback = True
        settings.save(update_fields=['digest_mode', 'email_feedback'])

        fixed_utc = datetime(2026, 6, 16, 10, 30, tzinfo=dt_timezone.utc)
        tz = ZoneInfo('Europe/Zurich')
        expected_boundary = fixed_utc.astimezone(tz).replace(minute=0, second=0, microsecond=0)

        with patch('django.utils.timezone.now', return_value=fixed_utc):
            dispatch_event(
                event_type=EventType.FEEDBACK,
                recipients=[student],
                title='Teacher feedback',
                body='Nice work',
                url='/journal/1/',
                dedupe_key='feedback:digest-email-1',
                email_subject='Teacher feedback',
                email_body='Nice work',
            )

        self.assertEqual(len(mail.outbox), 0)

        digest_item = NotificationDigestItem.objects.get(
            recipient=student,
            channel=NotificationDigestItem.Channel.EMAIL,
            digest_bucket=NotificationDigestItem.DigestBucket.HOURLY,
            event_key='feedback:digest-email-1',
        )
        self.assertEqual(digest_item.status, NotificationDigestItem.Status.QUEUED)
        self.assertEqual(digest_item.scheduled_for, expected_boundary)

        log = NotificationDeliveryLog.objects.get(
            recipient=student,
            channel=NotificationDeliveryLog.Channel.EMAIL,
            event_key='feedback:digest-email-1',
        )
        self.assertEqual(log.status, NotificationDeliveryLog.Status.QUEUED)

        with patch('django.utils.timezone.now', return_value=fixed_utc):
            dispatch_hourly_notification_digests_task()

        digest_item.refresh_from_db()
        self.assertEqual(digest_item.status, NotificationDigestItem.Status.SENT)
        log.refresh_from_db()
        self.assertEqual(log.status, NotificationDeliveryLog.Status.SENT)
        self.assertEqual(len(mail.outbox), 1)


class DigestModeSlackTests(TestCase):
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('accounts.slack_provider.send_user_dm', return_value='1234.5678')
    def test_hourly_slack_queues_and_dispatches(self, _mock_send_dm):
        student = make_student('digest-slack@example.com', email_notifications_enabled=False)
        settings = get_notification_settings(student)
        settings.digest_mode = settings.DigestMode.HOURLY
        settings.slack_enabled = True
        settings.slack_feedback = True
        settings.save(update_fields=['digest_mode', 'slack_enabled', 'slack_feedback'])

        integration = SlackIntegration.objects.create(
            user=student,
            slack_user_id='U999',
            slack_team_id='T999',
        )
        integration.set_access_token('xoxp-token')
        integration.save()

        fixed_utc = datetime(2026, 6, 16, 10, 30, tzinfo=dt_timezone.utc)

        with patch('django.utils.timezone.now', return_value=fixed_utc):
            dispatch_event(
                event_type=EventType.FEEDBACK,
                recipients=[student],
                title='Teacher feedback',
                body='Nice work',
                url='/journal/1/',
                dedupe_key='feedback:digest-slack-1',
                slack_text='Feedback arrived: Nice work',
            )

        digest_item = NotificationDigestItem.objects.get(
            recipient=student,
            channel=NotificationDigestItem.Channel.SLACK,
            digest_bucket=NotificationDigestItem.DigestBucket.HOURLY,
            event_key='feedback:digest-slack-1',
        )
        self.assertEqual(digest_item.status, NotificationDigestItem.Status.QUEUED)

        with patch('django.utils.timezone.now', return_value=fixed_utc):
            dispatch_hourly_notification_digests_task()

        digest_item.refresh_from_db()
        self.assertEqual(digest_item.status, NotificationDigestItem.Status.SENT)
        log = NotificationDeliveryLog.objects.get(
            recipient=student,
            channel=NotificationDeliveryLog.Channel.SLACK,
            event_key='feedback:digest-slack-1',
        )
        self.assertEqual(log.status, NotificationDeliveryLog.Status.SENT)
        self.assertEqual(_mock_send_dm.call_count, 1)

