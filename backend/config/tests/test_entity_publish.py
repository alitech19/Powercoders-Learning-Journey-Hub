from datetime import timedelta
from unittest.mock import patch

from django.http import QueryDict
from django.test import TestCase
from django.utils import timezone

from config.entity_publish import (
    apply_publish_schedule_from_post,
    cancel_scheduled_publish,
    is_draft_entity,
    parse_scheduled_publish_at,
    publish_entity_now,
    should_defer_assignment_notifications,
)
from goals.models import Goal, GoalEnrollment
from goals.services import create_goals_bulk
from tasks.models import Task
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.goals import make_staff_goal
from test_utils.tasks import make_staff_individual_task
from test_utils.users import make_student, make_teacher
from workflows.models import Workflow


class ScheduledPublishTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.teacher = make_teacher('sched-teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student('sched-student@example.com', group=self.group)

    def test_parse_scheduled_publish_at_requires_future(self):
        past = timezone.localtime() - timedelta(hours=1)
        post = QueryDict(mutable=True)
        post.update({
            'enable_scheduled_publish': 'on',
            'scheduled_publish_at': past.strftime('%Y-%m-%dT%H:%M'),
        })
        with self.assertRaises(Exception):
            parse_scheduled_publish_at(post)

    @patch('config.entity_publish._enqueue_publish_task')
    def test_apply_schedule_on_draft_goal(self, mock_enqueue):
        goal = make_staff_goal(self.teacher, visibility=Goal.Visibility.PRIVATE)
        GoalEnrollment.objects.create(goal=goal, student=self.student)
        future = timezone.localtime() + timedelta(days=1)
        post = QueryDict(mutable=True)
        post.update({
            'enable_scheduled_publish': 'on',
            'scheduled_publish_at': future.strftime('%Y-%m-%dT%H:%M'),
        })
        apply_publish_schedule_from_post(entity=goal, post=post, actor=self.teacher)
        goal.refresh_from_db()
        self.assertTrue(is_draft_entity(goal))
        self.assertIsNotNone(goal.scheduled_publish_at)
        mock_enqueue.assert_called_once()
        self.assertTrue(should_defer_assignment_notifications(goal))

    @patch('config.entity_publish.notify_students_for_entity')
    def test_manual_publish_cancels_schedule_and_notifies(self, mock_notify):
        goal = make_staff_goal(self.teacher, visibility=Goal.Visibility.PRIVATE)
        goal.scheduled_publish_at = timezone.now() + timedelta(days=2)
        goal.scheduled_publish_task_id = 'fake-task-id'
        goal.save(update_fields=['scheduled_publish_at', 'scheduled_publish_task_id'])
        GoalEnrollment.objects.create(goal=goal, student=self.student)

        post = QueryDict(mutable=True)
        post.update({'visibility': Goal.Visibility.SHARED})
        goal.visibility = Goal.Visibility.SHARED
        goal.save(update_fields=['visibility'])

        with patch('config.entity_publish.cancel_scheduled_publish') as mock_cancel:
            apply_publish_schedule_from_post(
                entity=goal,
                post=post,
                actor=self.teacher,
                previous_visibility=Goal.Visibility.PRIVATE,
            )
            mock_cancel.assert_called_once()
        mock_notify.assert_called_once()

    @patch('config.entity_publish._enqueue_publish_task')
    def test_create_goals_bulk_defers_notifications_when_scheduled(self, mock_enqueue):
        future = timezone.localtime() + timedelta(days=1)
        post = QueryDict(mutable=True)
        post.update({
            'title': 'Scheduled goal',
            'assignee_type': 'group',
            'assignee_target_id': str(self.group.pk),
            'visibility': Goal.Visibility.PRIVATE,
            'enable_scheduled_publish': 'on',
            'scheduled_publish_at': future.strftime('%Y-%m-%dT%H:%M'),
        })
        post.setlist('student_ids', [str(self.student.pk)])

        with patch('accounts.notifications.scheduling.schedule_goal_assigned') as mock_schedule:
            goal = create_goals_bulk(user=self.teacher, post=post)
            mock_schedule.assert_not_called()
        self.assertTrue(should_defer_assignment_notifications(goal))

    @patch('config.entity_publish.notify_students_for_entity')
    def test_publish_entity_now_makes_goal_shared(self, mock_notify):
        goal = make_staff_goal(self.teacher, visibility=Goal.Visibility.PRIVATE)
        goal.scheduled_publish_at = timezone.now() - timedelta(minutes=1)
        goal.save(update_fields=['scheduled_publish_at'])
        GoalEnrollment.objects.create(goal=goal, student=self.student)

        self.assertTrue(publish_entity_now('goal', goal.pk))
        goal.refresh_from_db()
        self.assertEqual(goal.visibility, Goal.Visibility.SHARED)
        self.assertIsNone(goal.scheduled_publish_at)
        mock_notify.assert_called_once()

    def test_cancel_clears_fields(self):
        task = make_staff_individual_task(self.teacher, visibility=Task.Visibility.PRIVATE)
        task.scheduled_publish_at = timezone.now() + timedelta(days=1)
        task.scheduled_publish_task_id = 'task-123'
        task.save(update_fields=['scheduled_publish_at', 'scheduled_publish_task_id'])
        with patch('config.celery.app.control.revoke'):
            cancel_scheduled_publish(task)
        task.refresh_from_db()
        self.assertIsNone(task.scheduled_publish_at)
        self.assertEqual(task.scheduled_publish_task_id, '')

    def test_workflow_private_is_draft(self):
        workflow = Workflow.objects.create(
            title='Draft wf',
            progress_mode=Workflow.ProgressMode.SHARED,
            assignee_type=Workflow.AssigneeType.GROUP,
            assignee_group=self.group,
            created_by=self.teacher,
            visibility=Workflow.Visibility.PRIVATE,
        )
        self.assertTrue(is_draft_entity(workflow))
