from django.test import TestCase

from goals.feedback_handlers import can_add_enrollment_feedback, can_view_enrollment_feedback
from goals.models import Goal
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.goals import enroll_student, make_staff_goal, make_student_goal
from test_utils.users import make_student, make_teacher


class GoalFeedbackHandlerTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
        )

    def test_student_views_feedback_on_shared_staff_goal(self):
        goal = make_staff_goal(self.teacher, visibility=Goal.Visibility.SHARED)
        enrollment = enroll_student(goal, self.student)
        self.assertTrue(can_view_enrollment_feedback(self.student, enrollment))
        self.assertFalse(can_add_enrollment_feedback(self.student, enrollment))

    def test_teacher_adds_feedback_on_shared_goal(self):
        goal = make_staff_goal(self.teacher, visibility=Goal.Visibility.SHARED)
        enrollment = enroll_student(goal, self.student)
        self.assertTrue(can_add_enrollment_feedback(self.teacher, enrollment))

    def test_teacher_cannot_add_on_private_staff_goal(self):
        goal = make_staff_goal(self.teacher, visibility=Goal.Visibility.PRIVATE)
        enrollment = enroll_student(goal, self.student)
        self.assertFalse(can_add_enrollment_feedback(self.teacher, enrollment))

    def test_student_own_goal_private_no_teacher_feedback(self):
        goal = make_student_goal(self.student, visibility=Goal.Visibility.PRIVATE)
        enrollment = goal.enrollments.get()
        self.assertTrue(can_view_enrollment_feedback(self.student, enrollment))
        self.assertFalse(can_add_enrollment_feedback(self.teacher, enrollment))
