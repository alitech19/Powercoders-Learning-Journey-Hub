from datetime import date

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import Notification
from accounts.notifications.staff_events import (
    get_teachers_for_student,
    notify_bug_report_new,
    notify_student_deadline_overdue,
    notify_student_task_completed,
)
from bug_reports.models import BugReport
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.tasks import enroll_student, make_group_shared_task
from test_utils.users import login_as, make_admin, make_student, make_teacher


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class StaffNotificationTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.teacher = make_teacher('teacher@example.com')
        self.student = make_student('student@example.com', group=self.group)
        assign_teacher(self.group, self.teacher)
        self.admin = make_admin('admin@example.com')

    def test_get_teachers_for_student_returns_group_teachers(self):
        teachers = get_teachers_for_student(self.student)
        self.assertEqual([t.pk for t in teachers], [self.teacher.pk])

    def test_notify_student_task_completed_notifies_teacher_and_admin(self):
        task = make_group_shared_task(self.teacher, self.group)
        enroll_student(task, self.student)
        notify_student_task_completed(student=self.student, task=task)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.teacher,
                title__contains='completed a task',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.admin,
                title__contains='completed a task',
            ).exists()
        )
        self.assertFalse(Notification.objects.filter(recipient=self.student).exists())

    def test_notify_student_deadline_overdue_notifies_teacher(self):
        notify_student_deadline_overdue(
            student=self.student,
            kind='task',
            item_id=42,
            title='Late homework',
            detail_url='/tasks/42/',
            dedupe_day=date.today().isoformat(),
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.teacher,
                title__contains='missed a task deadline',
            ).exists()
        )

    def test_notify_bug_report_new_notifies_admin(self):
        report = BugReport.objects.create(
            reporter=self.student,
            page_url='http://localhost/tasks/',
            page_path='/tasks/',
            description='Button broken',
        )
        notify_bug_report_new(report=report)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.admin,
                title__contains='bug report',
            ).exists()
        )


class TeacherNotificationSettingsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = make_teacher('teacher-settings@example.com')
        login_as(self.client, self.teacher)

    def test_teacher_sees_student_activity_rows(self):
        response = self.client.get(reverse('accounts:notification_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Student completed a task')
        self.assertContains(response, 'Student missed a deadline')
        self.assertNotContains(response, 'Feedback from teachers')


class AdminNotificationSettingsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin('admin-settings@example.com')
        login_as(self.client, self.admin)

    def test_admin_sees_teacher_and_platform_rows(self):
        response = self.client.get(reverse('accounts:notification_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Student completed a task')
        self.assertContains(response, 'Student missed a deadline')
        self.assertContains(response, 'New bug report submitted')
        self.assertContains(response, 'New user account created')
        self.assertNotContains(response, 'Feedback from teachers')
