from django.core.exceptions import ValidationError
from django.test import TestCase

from goals.models import Goal, GoalEnrollment, Milestone, MilestoneCompletion
from goals.services import (
    AssigneeType,
    create_student_goal,
    normalize_milestone_title,
    parse_milestones_from_post,
    sync_enrollment_status_from_milestones,
    sync_milestones,
    toggle_milestone_completion,
)
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.goals import add_milestone, make_student_goal
from test_utils.users import make_student, make_teacher


class GoalServicesTests(TestCase):
    def setUp(self):
        self.student = make_student('student@example.com')

    def test_normalize_milestone_title_unwraps_dict_string(self):
        raw = "{'title': 'Real title'}"
        self.assertEqual(normalize_milestone_title(raw), 'Real title')

    def test_parse_milestones_from_post_sorted_keys(self):
        post = {'ms_2': 'Second', 'ms_1': 'First'}
        milestones = parse_milestones_from_post(post)
        self.assertEqual([m['title'] for m in milestones], ['First', 'Second'])
        self.assertEqual([m['order'] for m in milestones], [0, 1])

    def test_sync_milestones_preserves_completions_on_rename(self):
        goal = make_student_goal(self.student, title='G')
        enrollment = goal.enrollments.get()
        old_ms = add_milestone(goal, title='Old', order=0)
        MilestoneCompletion.objects.create(enrollment=enrollment, milestone=old_ms)

        class PostDict(dict):
            def getlist(self, key):
                return super().get(key, [])

        sync_milestones(goal, PostDict({'ms_0': 'Renamed'}))
        self.assertEqual(goal.milestones.count(), 1)
        self.assertEqual(goal.milestones.first().title, 'Renamed')
        self.assertTrue(
            MilestoneCompletion.objects.filter(
                enrollment=enrollment,
                milestone=goal.milestones.first(),
            ).exists()
        )

    def test_create_student_goal_requires_title(self):
        class EmptyPost(dict):
            def getlist(self, key):
                return []

        with self.assertRaises(ValidationError):
            create_student_goal(user=self.student, post=EmptyPost({'description': 'x'}))

    def test_toggle_milestone_updates_enrollment_status(self):
        goal = make_student_goal(self.student)
        enrollment = goal.enrollments.get()
        ms = Milestone.objects.create(goal=goal, title='M1', order=0)
        self.assertEqual(enrollment.status, GoalEnrollment.Status.NOT_STARTED)

        toggle_milestone_completion(enrollment, ms)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, GoalEnrollment.Status.IN_PROGRESS)

        toggle_milestone_completion(enrollment, ms)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, GoalEnrollment.Status.NOT_STARTED)

    def test_sync_enrollment_status_skips_completed(self):
        goal = make_student_goal(self.student)
        enrollment = goal.enrollments.get()
        enrollment.status = GoalEnrollment.Status.COMPLETED
        enrollment.save(update_fields=['status'])
        sync_enrollment_status_from_milestones(enrollment)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, GoalEnrollment.Status.COMPLETED)


class GoalBulkServicesTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            's@example.com',
            cohort=self.cohort,
            group=self.group,
        )

    def test_create_goals_bulk_for_group(self):
        from goals.services import create_goals_bulk

        class Post(dict):
            def getlist(self, key):
                if key == 'student_ids':
                    return [str(self['student_ids'])]
                return super().get(key, [])

        goal = create_goals_bulk(
            user=self.teacher,
            post=Post(
                {
                    'title': 'Bulk goal',
                    'assignee_type': AssigneeType.GROUP,
                    'assignee_target_id': str(self.group.pk),
                    'student_ids': str(self.student.pk),
                    'visibility': Goal.Visibility.SHARED,
                    'ms_0': 'Step one',
                }
            ),
        )
        self.assertTrue(goal.is_staff_assigned)
        self.assertEqual(goal.enrollments.count(), 1)
        self.assertEqual(goal.milestones.count(), 1)
