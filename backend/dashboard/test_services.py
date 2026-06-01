from datetime import date, datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from dashboard.services import (
    students_missing_weekly_reflection,
    this_week_monday,
    user_has_weekly_reflection_this_week,
)
from reflections.constants import FINAL_REFLECTION_TEMPLATE, TAG_WEEKLY
from test_utils.cohorts import make_cohort, make_group
from test_utils.reflections import make_reflection
from test_utils.users import make_student

_WEDNESDAY = date(2026, 5, 27)
_WEEK_START = timezone.make_aware(datetime.combine(date(2026, 5, 25), datetime.min.time()))


class DashboardServicesTests(TestCase):
    @patch('dashboard.services.date')
    def test_this_week_monday(self, mock_date):
        mock_date.today.return_value = _WEDNESDAY
        self.assertEqual(this_week_monday(), date(2026, 5, 25))

    @patch('dashboard.services.week_start_datetime')
    @patch('dashboard.services.date')
    def test_user_has_weekly_reflection_when_final_submitted_this_week(
        self, mock_date, mock_week_start,
    ):
        mock_date.today.return_value = _WEDNESDAY
        mock_week_start.return_value = _WEEK_START
        student = make_student('s@example.com')
        make_reflection(
            student,
            tags=[TAG_WEEKLY],
            final_reflection='Submitted this week.',
            final_reflection_at=_WEEK_START,
        )
        self.assertTrue(user_has_weekly_reflection_this_week(student))

    @patch('dashboard.services.week_start_datetime')
    @patch('dashboard.services.date')
    def test_user_missing_weekly_without_final(self, mock_date, mock_week_start):
        mock_date.today.return_value = _WEDNESDAY
        mock_week_start.return_value = _WEEK_START
        student = make_student('s@example.com')
        make_reflection(
            student,
            tags=[TAG_WEEKLY],
            final_reflection=FINAL_REFLECTION_TEMPLATE,
        )
        self.assertFalse(user_has_weekly_reflection_this_week(student))

    @patch('dashboard.services.week_start_datetime')
    def test_students_missing_weekly_reflection_list(self, mock_week_start):
        mock_week_start.return_value = _WEEK_START
        cohort = make_cohort()
        group = make_group(cohort)
        done = make_student('done@example.com', cohort=cohort, group=group)
        missing = make_student('miss@example.com', cohort=cohort, group=group)
        make_reflection(
            done,
            tags=[TAG_WEEKLY],
            final_reflection='Done.',
            final_reflection_at=_WEEK_START,
        )
        missing_list = students_missing_weekly_reflection([done, missing])
        self.assertEqual(len(missing_list), 1)
        self.assertEqual(missing_list[0].pk, missing.pk)
