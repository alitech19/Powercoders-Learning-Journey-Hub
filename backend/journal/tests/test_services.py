from datetime import date, timedelta

from django.test import TestCase

from journal.services import writing_streak
from test_utils.journal import make_journal_entry
from test_utils.users import make_student


class JournalServicesTests(TestCase):
    def setUp(self):
        self.student = make_student('s@example.com')

    def test_writing_streak_zero_when_no_entries(self):
        self.assertEqual(writing_streak(self.student), 0)

    def test_writing_streak_counts_consecutive_days(self):
        today = date.today()
        make_journal_entry(self.student, entry_date=today)
        make_journal_entry(self.student, entry_date=today - timedelta(days=1))
        make_journal_entry(self.student, entry_date=today - timedelta(days=2))
        self.assertEqual(writing_streak(self.student), 3)

    def test_writing_streak_stops_at_gap(self):
        today = date.today()
        make_journal_entry(self.student, entry_date=today)
        make_journal_entry(self.student, entry_date=today - timedelta(days=2))
        self.assertEqual(writing_streak(self.student), 1)
