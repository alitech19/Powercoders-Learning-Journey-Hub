from datetime import time, timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Notification, NotificationDeliveryLog
from accounts.notifications.settings import get_notification_settings
from accounts.tasks import run_deadline_reminders_task
from goals.models import GoalEnrollment
from tasks.models import Task
from test_utils.goals import enroll_student as enroll_goal_student
from test_utils.goals import make_staff_goal
from test_utils.tasks import enroll_student as enroll_task_student
from test_utils.tasks import make_staff_individual_task
from test_utils.users import make_student, make_teacher


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class DeadlineReminderTests(TestCase):
    def setUp(self):
        self.teacher = make_teacher('teacher-rem@example.com')
        self.student = make_student('student-rem@example.com')
        settings = get_notification_settings(self.student)
        settings.email_deadline_reminder = True
        settings.slack_deadline_reminder = False
        settings.save(update_fields=['email_deadline_reminder', 'slack_deadline_reminder'])

    def test_sends_24h_reminder_for_task(self):
        task = make_staff_individual_task(
            self.teacher,
            visibility=Task.Visibility.SHARED,
            due_date=timezone.localdate() + timedelta(days=1),
            title='Task due tomorrow',
        )
        enroll_task_student(task, self.student)

        run_deadline_reminders_task()

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                title__icontains='Task due tomorrow',
            ).exists()
        )

    def test_sends_overdue_reminder_for_goal(self):
        goal = make_staff_goal(
            self.teacher,
            target_date=timezone.localdate() - timedelta(days=1),
            title='Goal overdue',
        )
        enroll_goal_student(goal, self.student, status=GoalEnrollment.Status.IN_PROGRESS)

        run_deadline_reminders_task()

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                title__icontains='Goal overdue',
            ).exists()
        )

    def test_skips_channel_in_quiet_hours(self):
        task = make_staff_individual_task(
            self.teacher,
            visibility=Task.Visibility.SHARED,
            due_date=timezone.localdate(),
            title='Quiet task',
        )
        enroll_task_student(task, self.student)
        settings = get_notification_settings(self.student)
        settings.quiet_hours_start = time(0, 0)
        settings.quiet_hours_end = time(23, 59)
        settings.save(update_fields=['quiet_hours_start', 'quiet_hours_end'])

        run_deadline_reminders_task()

        self.assertTrue(
            NotificationDeliveryLog.objects.filter(
                recipient=self.student,
                channel=NotificationDeliveryLog.Channel.EMAIL,
                status=NotificationDeliveryLog.Status.SKIPPED,
            ).exists()
        )
