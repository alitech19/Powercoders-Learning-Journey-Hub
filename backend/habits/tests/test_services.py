from datetime import date, timedelta

from django.test import TestCase

from habits.models import HabitLog
from habits.services import (
    get_current_weekly_streak,
    get_done_count_for_week,
    get_week_start,
    is_habit_week_successful,
)
from test_utils.habits import log_habit, make_habit
from test_utils.users import make_student


class HabitServicesTests(TestCase):
    def setUp(self):
        self.student = make_student('s@example.com')
        self.habit = make_habit(self.student, target_days_per_week=2)
        self.monday = date(2026, 5, 25)

    def test_week_start_is_monday(self):
        wednesday = date(2026, 5, 27)
        self.assertEqual(get_week_start(wednesday), self.monday)

    def test_done_count_and_week_success(self):
        log_habit(self.habit, self.monday)
        log_habit(self.habit, self.monday + timedelta(days=1))
        self.assertEqual(get_done_count_for_week(self.habit, self.monday), 2)
        self.assertTrue(is_habit_week_successful(self.habit, self.monday))

    def test_streak_counts_successful_weeks(self):
        log_habit(self.habit, self.monday)
        log_habit(self.habit, self.monday + timedelta(days=2))
        prev_monday = self.monday - timedelta(days=7)
        log_habit(self.habit, prev_monday)
        log_habit(self.habit, prev_monday + timedelta(days=1))
        streak = get_current_weekly_streak(self.habit, today=self.monday + timedelta(days=3))
        self.assertGreaterEqual(streak, 1)

    def test_not_done_logs_do_not_count(self):
        log_habit(self.habit, self.monday, status=HabitLog.Status.NOT_DONE)
        self.assertEqual(get_done_count_for_week(self.habit, self.monday), 0)
        self.assertFalse(is_habit_week_successful(self.habit, self.monday))
