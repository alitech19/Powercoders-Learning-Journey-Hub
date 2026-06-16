from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import Notification, NotificationDeliveryLog, UserNotificationSettings
from accounts.notifications.constants import EventType
from accounts.notifications.dispatcher import dispatch_event
from accounts.notifications.settings import get_notification_settings, sync_email_enabled
from test_utils.users import login_as, make_student


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class DispatchEventTests(TestCase):
    def setUp(self):
        mail.outbox.clear()
        self.student = make_student('dispatch@example.com', email_notifications_enabled=True)

    def test_creates_in_app_notification_and_delivery_log(self):
        dispatch_event(
            event_type=EventType.FEEDBACK,
            recipients=[self.student],
            title='Teacher left feedback',
            body='Nice work',
            url='/journal/1/',
            dedupe_key='feedback:1',
            email_subject='Teacher left feedback',
            email_body='Nice work',
        )
        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 1)
        self.assertEqual(
            NotificationDeliveryLog.objects.filter(
                recipient=self.student,
                channel=NotificationDeliveryLog.Channel.IN_APP,
                status=NotificationDeliveryLog.Status.SENT,
            ).count(),
            1,
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_dedupes_repeat_dispatch(self):
        kwargs = dict(
            event_type=EventType.FEEDBACK,
            recipients=[self.student],
            title='Teacher left feedback',
            body='Nice work',
            url='/journal/1/',
            dedupe_key='feedback:dup',
            email_subject='Teacher left feedback',
            email_body='Nice work',
        )
        dispatch_event(**kwargs)
        dispatch_event(**kwargs)
        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_skips_email_when_user_disabled_notifications(self):
        self.student.email_notifications_enabled = False
        self.student.save(update_fields=['email_notifications_enabled'])
        sync_email_enabled(self.student, False)

        dispatch_event(
            event_type=EventType.FEEDBACK,
            recipients=[self.student],
            title='Teacher left feedback',
            body='Nice work',
            url='/journal/1/',
            dedupe_key='feedback:2',
            email_subject='Teacher left feedback',
            email_body='Nice work',
        )
        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 1)
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(
            NotificationDeliveryLog.objects.filter(
                recipient=self.student,
                channel=NotificationDeliveryLog.Channel.EMAIL,
                status=NotificationDeliveryLog.Status.SKIPPED,
            ).exists()
        )

    def test_skips_all_channels_when_event_disabled(self):
        settings = get_notification_settings(self.student)
        settings.email_feedback = False
        settings.slack_feedback = False
        settings.save(update_fields=['email_feedback', 'slack_feedback'])

        dispatch_event(
            event_type=EventType.FEEDBACK,
            recipients=[self.student],
            title='Teacher left feedback',
            body='Nice work',
            url='/journal/1/',
            dedupe_key='feedback:3',
        )
        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 1)
        self.assertEqual(len(mail.outbox), 0)


class NotificationSettingsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_student('settings@example.com')
        login_as(self.client, self.user)

    def test_get_settings_page(self):
        response = self.client.get(reverse('accounts:notification_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserNotificationSettings.objects.filter(user=self.user).exists())

    def test_post_updates_settings(self):
        response = self.client.post(
            reverse('accounts:notification_settings'),
            {
                'email_enabled': 'on',
                'email_feedback': 'on',
                'email_new_task': 'on',
                'email_new_goal': 'on',
                'email_new_workflow': 'on',
                'email_deadline_reminder': 'on',
                'email_group_chat_mentions': 'on',
                'slack_feedback': 'on',
                'slack_new_task': 'on',
                'slack_new_goal': 'on',
                'slack_new_workflow': 'on',
                'slack_deadline_reminder': 'on',
                'slack_group_chat_mentions': 'on',
                'timezone': 'Europe/Zurich',
            },
        )
        self.assertRedirects(response, reverse('accounts:notification_settings'))
        settings = UserNotificationSettings.objects.get(user=self.user)
        self.assertTrue(settings.email_feedback)
        self.assertFalse(settings.slack_group_chat_all_messages)
