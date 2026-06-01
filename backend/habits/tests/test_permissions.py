from django.test import TestCase

from habits.models import Habit
from habits.permissions import (
    can_edit_habit,
    can_log_habit,
    can_view_habit,
    get_visible_habits_for_user,
)
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.habits import make_habit
from test_utils.users import make_student, make_teacher


class HabitPermissionTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.teacher = make_teacher('t@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            's@example.com',
            cohort=self.cohort,
            group=self.group,
        )

    def test_student_edits_active_habit(self):
        habit = make_habit(self.student)
        self.assertTrue(can_view_habit(self.student, habit))
        self.assertTrue(can_edit_habit(self.student, habit))
        self.assertTrue(can_log_habit(self.student, habit))

    def test_cannot_edit_completed(self):
        habit = make_habit(self.student, status=Habit.Status.COMPLETED)
        self.assertFalse(can_edit_habit(self.student, habit))

    def test_teacher_views_shared(self):
        habit = make_habit(self.student, visibility=Habit.Visibility.SHARED)
        self.assertTrue(can_view_habit(self.teacher, habit))

    def test_teacher_not_private(self):
        habit = make_habit(self.student, visibility=Habit.Visibility.PRIVATE)
        self.assertFalse(can_view_habit(self.teacher, habit))
