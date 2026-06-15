from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from bug_reports.models import BugReport
from config.models import IntegratedModule
from config.module_access import invalidate_module_cache
from test_utils.users import login_as, make_admin, make_student


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class BugReportSubmitTests(TestCase):
    def setUp(self):
        invalidate_module_cache()
        self.student = make_student('student@example.com')
        self.client = Client()

    def test_student_can_submit_report(self):
        login_as(self.client, self.student)
        url = reverse('bug_reports:report_create') + '?from=/tasks/'
        response = self.client.post(
            url,
            {'description': 'Button does not work'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        report = BugReport.objects.get()
        self.assertEqual(report.reporter, self.student)
        self.assertIn('/tasks/', report.page_path)
        self.assertEqual(len(mail.outbox), 1)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('bug_reports:report_create'))
        self.assertEqual(response.status_code, 302)

    def test_module_disabled_shows_stub(self):
        IntegratedModule.objects.filter(slug='bug_reports').update(is_enabled=False)
        invalidate_module_cache()
        login_as(self.client, self.student)
        response = self.client.get(reverse('bug_reports:report_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bug reports is not available')


class BugReportInboxTests(TestCase):
    def setUp(self):
        invalidate_module_cache()
        self.admin_a = make_admin('admin-a@example.com')
        self.admin_b = make_admin('admin-b@example.com')
        self.student = make_student('student@example.com')
        self.report = BugReport.objects.create(
            reporter=self.student,
            page_url='http://localhost:8000/tasks/',
            page_path='/tasks/',
            description='Broken layout',
        )
        self.client = Client()

    def test_admin_can_view_inbox(self):
        login_as(self.client, self.admin_a)
        response = self.client.get(reverse('bug_reports:report_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'student@example.com')

    def test_student_cannot_view_inbox(self):
        login_as(self.client, self.student)
        response = self.client.get(reverse('bug_reports:report_list'))
        self.assertEqual(response.status_code, 302)

    def test_take_blocks_second_admin(self):
        login_as(self.client, self.admin_a)
        self.client.post(reverse('bug_reports:report_take', args=[self.report.pk]))
        self.report.refresh_from_db()
        self.assertEqual(self.report.assigned_to, self.admin_a)

        login_as(self.client, self.admin_b)
        response = self.client.post(
            reverse('bug_reports:report_take', args=[self.report.pk]),
            follow=True,
        )
        self.assertContains(response, 'Already handled by')

    def test_admin_reply_emails_reporter(self):
        login_as(self.client, self.admin_a)
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            mail.outbox.clear()
            self.client.post(
                reverse('bug_reports:report_reply', args=[self.report.pk]),
                {'body': 'We are looking into it.'},
            )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('We are looking into it', mail.outbox[0].body)
