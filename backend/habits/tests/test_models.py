from django.db import IntegrityError
from django.test import TestCase

from habits.models import Habit, HabitLog
from test_utils.habits import log_habit, make_habit
from test_utils.users import make_student


class HabitModelTests(TestCase):
    def setUp(self):
        self.student = make_student('s@example.com')

    def test_str_and_is_active(self):
        habit = make_habit(self.student, title='Read')
        self.assertIn('Read', str(habit))
        self.assertTrue(habit.is_active)
        habit.status = Habit.Status.COMPLETED
        self.assertFalse(habit.is_active)

    def test_unique_log_per_day(self):
        habit = make_habit(self.student)
        from datetime import date

        day = date(2026, 5, 26)
        log_habit(habit, day)
        with self.assertRaises(IntegrityError):
            log_habit(habit, day, status=HabitLog.Status.NOT_DONE)
