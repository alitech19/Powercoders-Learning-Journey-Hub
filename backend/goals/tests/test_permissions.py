from django.test import TestCase

from goals.models import Goal
from goals.permissions import (
    can_manage_goal,
    can_view_goal,
    get_visible_goals_for_user,
    is_staff_assigned,
)
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.goals import enroll_student, make_goal, make_staff_goal, make_student_goal
from test_utils.users import make_admin, make_student, make_teacher


class GoalPermissionTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort, name='G1')
        self.other_group = make_group(self.cohort, name='G2')
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
        )
        self.other_student = make_student(
            'other@example.com',
            cohort=self.cohort,
            group=self.other_group,
        )
        self.admin = make_admin('admin@example.com')

    def test_student_sees_own_enrolled_goal(self):
        goal = make_student_goal(self.student, visibility=Goal.Visibility.SHARED)
        self.assertTrue(can_view_goal(self.student, goal))

    def test_student_cannot_see_unenrolled_goal(self):
        goal = make_student_goal(self.other_student)
        self.assertFalse(can_view_goal(self.student, goal))

    def test_student_cannot_see_staff_private_draft(self):
        goal = make_staff_goal(self.teacher, visibility=Goal.Visibility.PRIVATE)
        enroll_student(goal, self.student)
        self.assertFalse(can_view_goal(self.student, goal))

    def test_teacher_sees_shared_staff_goal_in_scope(self):
        goal = make_staff_goal(self.teacher, visibility=Goal.Visibility.SHARED)
        enroll_student(goal, self.student)
        self.assertTrue(can_view_goal(self.teacher, goal))
        self.assertTrue(can_manage_goal(self.teacher, goal))

    def test_teacher_cannot_see_out_of_scope_enrollment(self):
        goal = make_staff_goal(self.teacher, visibility=Goal.Visibility.SHARED)
        enroll_student(goal, self.other_student)
        self.assertFalse(can_view_goal(self.teacher, goal))

    def test_student_manages_own_goal(self):
        goal = make_student_goal(self.student)
        self.assertTrue(can_manage_goal(self.student, goal))

    def test_is_staff_assigned(self):
        goal = make_staff_goal(self.teacher)
        self.assertTrue(is_staff_assigned(goal))
        self.assertFalse(is_staff_assigned(make_student_goal(self.student)))

    def test_visible_goals_for_student(self):
        mine = make_student_goal(self.student, title='Mine')
        make_student_goal(self.other_student, title='Other')
        titles = set(get_visible_goals_for_user(self.student).values_list('title', flat=True))
        self.assertEqual(titles, {'Mine'})
        self.assertIn(mine.title, titles)
