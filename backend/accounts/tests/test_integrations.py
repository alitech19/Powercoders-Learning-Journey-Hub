"""Slack, email, and Celery integration behaviour (not only view mocks)."""

import io
import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.emails import (
    notify_feedback_received,
    send_new_user_slack,
    send_welcome_email,
)
from accounts.models import Notification, User
from accounts.slack import send_slack_message
from accounts.tasks import notify_missing_reflections
from feedback.models import FeedbackEntry
from journal.models import JournalEntry
from reflections.constants import TAG_WEEKLY
from test_utils.reflections import make_reflection
from test_utils.users import login_as, make_admin, make_student, make_teacher

_WEEK_START = timezone.make_aware(datetime.combine(date(2026, 5, 25), datetime.min.time()))


class SlackMessageTests(TestCase):
    @override_settings(SLACK_WEBHOOK_URL='')
    def test_empty_webhook_is_no_op(self):
        with patch('urllib.request.urlopen') as mock_open:
            send_slack_message('hello')
        mock_open.assert_not_called()

    @override_settings(SLACK_WEBHOOK_URL='https://hooks.slack.com/services/TEST')
    @patch('urllib.request.urlopen')
    def test_posts_json_payload(self, mock_urlopen):
        mock_urlopen.return_value = MagicMock()
        send_slack_message('Test *bold*')
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, 'https://hooks.slack.com/services/TEST')
        body = json.loads(req.data.decode())
        self.assertEqual(body['text'], 'Test *bold*')

    @override_settings(SLACK_WEBHOOK_URL='https://hooks.slack.com/services/TEST')
    @patch('urllib.request.urlopen', side_effect=OSError('network down'))
    def test_network_errors_do_not_raise(self, _mock_urlopen):
        send_slack_message('still ok')


@override_settings(
    SITE_URL='http://testserver',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class WelcomeEmailTests(TestCase):
    def setUp(self):
        mail.outbox.clear()

    def test_send_welcome_email_delivers_to_outbox(self):
        user = make_student('welcome@example.com', display_name='Welcome User')
        send_welcome_email(user, 'Temp-Pass-99')
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, [user.email])
        self.assertIn('Temp-Pass-99', msg.body)
        self.assertIn('http://testserver/account/login/', msg.body)

    @patch('accounts.emails.send_slack_message')
    def test_send_new_user_slack_formats_message(self, mock_slack):
        user = make_student('slack-new@example.com', display_name='Slack New')
        send_new_user_slack(user)
        mock_slack.assert_called_once()
        self.assertIn('Slack New', mock_slack.call_args[0][0])
        self.assertIn('slack-new@example.com', mock_slack.call_args[0][0])


@override_settings(
    SITE_URL='http://testserver',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class FeedbackEmailIntegrationTests(TestCase):
    def setUp(self):
        mail.outbox.clear()

    @patch('accounts.emails.send_slack_message')
    def test_sends_email_when_notifications_enabled(self, _mock_slack):
        student = make_student('fb@example.com', email_notifications_enabled=True)
        teacher = make_teacher('teach-fb@example.com')
        journal = JournalEntry.objects.create(
            author=student,
            title='Entry',
            content='Body',
            entry_date='2026-06-01',
        )
        ct = ContentType.objects.get_for_model(JournalEntry)
        entry = FeedbackEntry.objects.create(
            content_type=ct,
            object_id=journal.pk,
            author=teacher,
            body='Great job',
        )
        notify_feedback_received(
            entry=entry,
            recipient=student,
            title='Teacher left feedback',
            relative_url='/journal/1/',
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Great job', mail.outbox[0].body)

    @patch('accounts.emails.send_slack_message')
    def test_skips_email_when_notifications_disabled(self, _mock_slack):
        student = make_student(
            'nofb@example.com',
            email_notifications_enabled=False,
        )
        teacher = make_teacher('t2@example.com')
        journal = JournalEntry.objects.create(
            author=student,
            title='Entry',
            content='Body',
            entry_date='2026-06-01',
        )
        ct = ContentType.objects.get_for_model(JournalEntry)
        entry = FeedbackEntry.objects.create(
            content_type=ct,
            object_id=journal.pk,
            author=teacher,
            body='Note',
        )
        notify_feedback_received(
            entry=entry,
            recipient=student,
            title='Feedback',
            relative_url='/journal/1/',
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(Notification.objects.filter(recipient=student).exists())


@override_settings(
    SLACK_WEBHOOK_URL='https://hooks.slack.com/services/TEST',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class NotifyMissingReflectionsTaskTests(TestCase):
    @patch('urllib.request.urlopen')
    @patch('dashboard.services.students_missing_weekly_reflection')
    def test_task_posts_all_clear_when_none_missing(self, mock_missing, mock_urlopen):
        mock_missing.return_value = []
        mock_urlopen.return_value = MagicMock()
        notify_missing_reflections()
        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        self.assertIn('All students', body['text'])

    @patch('urllib.request.urlopen')
    @patch('dashboard.services.week_start_datetime')
    def test_task_lists_missing_students(self, mock_week_start, mock_urlopen):
        mock_week_start.return_value = _WEEK_START
        mock_urlopen.return_value = MagicMock()
        done = make_student('done@example.com', display_name='Done Student')
        missing = make_student('miss@example.com', display_name='Missing Student')
        make_reflection(
            done,
            tags=[TAG_WEEKLY],
            final_reflection='Submitted.',
            final_reflection_at=_WEEK_START,
        )
        notify_missing_reflections()
        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        self.assertIn('Missing Student', body['text'])
        self.assertNotIn('Done Student', body['text'])

    def test_task_registered_with_celery(self):
        from accounts.tasks import notify_missing_reflections as task

        self.assertTrue(getattr(task, 'delay', None))
        self.assertEqual(task.name, 'accounts.tasks.notify_missing_reflections')


@override_settings(
    SITE_URL='http://testserver',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class UserImportIntegrationTests(TestCase):
    def setUp(self):
        mail.outbox.clear()
        self.client = Client()
        self.admin = make_admin('import-admin@example.com')
        login_as(self.client, self.admin)

    @patch('accounts.emails.send_new_user_slack')
    def test_csv_import_sends_welcome_email(self, mock_slack):
        csv_content = 'email,display_name,role\nimported@example.com,Imported User,student\n'
        response = self.client.post(
            reverse('accounts:user_import'),
            {'csv_file': io.BytesIO(csv_content.encode('utf-8'))},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email='imported@example.com').exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['imported@example.com'])
        mock_slack.assert_called_once()

    @patch('accounts.emails.send_new_user_slack')
    def test_csv_import_admin_role_grants_full_admin_access(self, mock_slack):
        """Admin-role rows must get is_staff + is_superuser, or they either
        can't reach /admin/ at all, or land there seeing almost no app sections."""
        csv_content = 'email,display_name,role\nimportedadmin@example.com,Imported Admin,admin\n'
        self.client.post(
            reverse('accounts:user_import'),
            {'csv_file': io.BytesIO(csv_content.encode('utf-8'))},
        )
        imported_admin = User.objects.get(email='importedadmin@example.com')
        self.assertTrue(imported_admin.is_staff)
        self.assertTrue(imported_admin.is_superuser)
