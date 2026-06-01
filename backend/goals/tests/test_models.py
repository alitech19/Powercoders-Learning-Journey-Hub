from datetime import date, timedelta

from django.test import TestCase

from goals.models import Goal, GoalEnrollment, MilestoneCompletion
from test_utils.goals import add_milestone, enroll_student, make_goal, make_student_goal
from test_utils.users import make_student


class GoalModelTests(TestCase):
    def test_student_goal_str(self):
        student = make_student('s@example.com', display_name='Sam')
        goal = make_student_goal(student, title='Learn Python')
        self.assertIn('Sam', str(goal))
        self.assertIn('Learn Python', str(goal))

    def test_staff_assigned_goal_str_is_title_only(self):
        goal = make_goal(author=None, title='Template')
        self.assertEqual(str(goal), 'Template')
        self.assertTrue(goal.is_staff_assigned)

    def test_enrollment_str(self):
        student = make_student('s@example.com')
        goal = make_student_goal(student, title='G1')
        enrollment = goal.enrollments.get()
        self.assertIn('G1', str(enrollment))


class GoalEnrollmentProgressTests(TestCase):
    def setUp(self):
        self.student = make_student('s@example.com')
        self.goal = make_student_goal(self.student)
        self.enrollment = self.goal.enrollments.get()

    def test_progress_without_milestones_maps_status(self):
        self.assertEqual(self.enrollment.progress, 0)
        self.enrollment.status = GoalEnrollment.Status.IN_PROGRESS
        self.assertEqual(self.enrollment.progress, 50)
        self.enrollment.status = GoalEnrollment.Status.COMPLETED
        self.assertEqual(self.enrollment.progress, 100)

    def test_progress_with_milestones(self):
        m1 = add_milestone(self.goal, title='M1', order=1)
        add_milestone(self.goal, title='M2', order=2)
        MilestoneCompletion.objects.create(enrollment=self.enrollment, milestone=m1)
        self.assertEqual(self.enrollment.progress, 50)
        self.assertFalse(self.enrollment.all_milestones_complete)

    def test_is_overdue(self):
        self.goal.target_date = date.today() - timedelta(days=1)
        self.goal.save(update_fields=['target_date'])
        self.assertTrue(self.enrollment.is_overdue)
        self.enrollment.status = GoalEnrollment.Status.COMPLETED
        self.enrollment.save(update_fields=['status'])
        self.assertFalse(self.enrollment.is_overdue)
