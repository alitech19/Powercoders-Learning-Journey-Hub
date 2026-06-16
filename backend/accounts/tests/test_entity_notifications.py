from django.core import mail
from django.test import TestCase, override_settings

from accounts.models import Notification
from accounts.notifications.entity_events import (
    notify_goal_assigned,
    notify_task_assigned,
    notify_workflow_assigned,
)
from goals.models import Goal
from tasks.models import Task
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.goals import make_staff_goal
from test_utils.tasks import make_staff_individual_task
from test_utils.users import make_student, make_teacher
from test_utils.workflows import make_workflow
from workflows.models import Workflow


@override_settings(
    SITE_URL='http://testserver',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class EntityAssignmentNotificationTests(TestCase):
    def setUp(self):
        mail.outbox.clear()
        self.teacher = make_teacher('assign@example.com', display_name='Teacher Assign')
        self.student = make_student('assigned@example.com', display_name='Assigned Student')
        cohort = make_cohort()
        group = make_group(cohort)
        self.student.group = group
        self.student.cohort = cohort
        self.student.save(update_fields=['group', 'cohort'])
        assign_teacher(group, self.teacher)

    def test_notify_task_assigned_creates_in_app_notification(self):
        task = make_staff_individual_task(self.teacher, title='Read chapter 3', visibility=Task.Visibility.SHARED)
        task.enrollments.create(student=self.student, status=Task.Status.TODO)

        notify_task_assigned(task=task, students=[self.student], actor=self.teacher)

        notification = Notification.objects.get(recipient=self.student)
        self.assertIn('Read chapter 3', notification.title)
        self.assertEqual(len(mail.outbox), 1)

    def test_notify_task_skips_private_tasks(self):
        task = make_staff_individual_task(self.teacher, title='Draft task', visibility=Task.Visibility.PRIVATE)
        notify_task_assigned(task=task, students=[self.student], actor=self.teacher)
        self.assertFalse(Notification.objects.filter(recipient=self.student).exists())

    def test_notify_goal_assigned(self):
        goal = make_staff_goal(self.teacher, title='Learn Django', visibility=Goal.Visibility.SHARED)
        goal.enrollments.create(student=self.student)

        notify_goal_assigned(goal=goal, students=[self.student], actor=self.teacher)

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                title__icontains='Learn Django',
            ).exists()
        )

    def test_notify_workflow_assigned(self):
        workflow = make_workflow(
            self.teacher,
            title='Onboarding path',
            visibility=Workflow.Visibility.PUBLIC,
            progress_mode=Workflow.ProgressMode.INDIVIDUAL,
            assignee_group=self.student.group,
        )
        workflow.enrollments.create(student=self.student)

        notify_workflow_assigned(
            workflow=workflow,
            students=[self.student],
            actor=self.teacher,
        )

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                title__icontains='Onboarding path',
            ).exists()
        )

    def test_create_goals_bulk_sends_notification(self):
        from goals.services import create_goals_bulk

        class PostDict(dict):
            def getlist(self, key):
                return super().get(key, [])

        post = PostDict({
            'title': 'Bulk goal',
            'assignee_type': 'group',
            'assignee_target_id': str(self.student.group_id),
            'select_all_students': 'on',
            'visibility': Goal.Visibility.SHARED,
            'category': Goal.Category.TECHNICAL,
            'status': 'in_progress',
        })

        with self.captureOnCommitCallbacks(execute=True):
            create_goals_bulk(user=self.teacher, post=post)

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                title__icontains='Bulk goal',
            ).exists()
        )
