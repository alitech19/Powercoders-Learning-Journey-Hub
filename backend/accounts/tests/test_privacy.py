from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import Notification, User
from feedback.services import create_entry
from journal.models import JournalEntry
from test_utils.users import DEFAULT_PASSWORD, login_as, make_student, make_teacher


class DataExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_student('export@example.com', display_name='Exporter')
        login_as(self.client, self.user)
        JournalEntry.objects.create(
            author=self.user,
            title='Day one',
            content='Hello world',
            entry_date='2026-01-01',
        )

    def test_export_returns_markdown_attachment(self):
        response = self.client.get(reverse('accounts:data_export'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/markdown', response['Content-Type'])
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn(b'# Powercoders Data Export', response.content)
        self.assertIn(b'Day one', response.content)
        self.assertIn(b'Journal entries', response.content)

    def test_export_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('accounts:data_export'))
        self.assertEqual(response.status_code, 302)


class DeleteOwnAccountTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_student('delete@example.com')
        login_as(self.client, self.user)

    def test_wrong_password_shows_error(self):
        response = self.client.post(
            reverse('accounts:delete_own_account'),
            {'password': 'wrong'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incorrect password')
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_correct_password_deletes_user(self):
        response = self.client.post(
            reverse('accounts:delete_own_account'),
            {'password': DEFAULT_PASSWORD},
        )
        self.assertRedirects(response, reverse('accounts:account_deleted'))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())


class NotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = make_student('notif@example.com')
        self.teacher = make_teacher('teach@example.com')
        login_as(self.client, self.student)

    def test_notifications_list_marks_read(self):
        Notification.objects.create(
            recipient=self.student,
            title='Test',
            body='Body',
            is_read=False,
        )
        response = self.client.get(reverse('accounts:notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Notification.objects.filter(recipient=self.student, is_read=False).exists()
        )


@override_settings(SITE_URL='http://testserver')
class FeedbackNotificationTests(TestCase):
    def test_create_entry_notifies_student(self):
        student = make_student('stu@example.com')
        teacher = make_teacher('t@example.com')
        entry = JournalEntry.objects.create(
            author=student,
            title='Shared entry',
            content='Content',
            entry_date='2026-02-01',
            visibility=JournalEntry.Visibility.SHARED,
        )
        with patch('accounts.emails.send_mail'), patch('accounts.emails.send_slack_message'):
            fb = create_entry(target=entry, author=teacher, body='Nice work!')
        self.assertIsNotNone(fb)
        self.assertTrue(
            Notification.objects.filter(recipient=student, title__icontains='feedback').exists()
        )


class WelcomeEmailTests(TestCase):
    @patch('accounts.emails.send_new_user_slack')
    @patch('accounts.emails.send_welcome_email')
    def test_user_create_calls_integrations(self, mock_email, mock_slack):
        from test_utils.users import make_admin

        admin = make_admin('admin@example.com')
        login_as(self.client, admin)
        response = self.client.post(
            reverse('accounts:user_create'),
            {
                'email': 'newuser@example.com',
                'display_name': 'New User',
                'role': User.Role.STUDENT,
            },
        )
        self.assertEqual(response.status_code, 200)
        mock_email.assert_called_once()
        mock_slack.assert_called_once()
