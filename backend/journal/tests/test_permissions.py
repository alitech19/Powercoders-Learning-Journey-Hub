from django.test import TestCase

from journal.models import JournalEntry
from journal.permissions import (
    can_create_journal_entries,
    can_delete_journal_entry,
    can_view_journal_entry,
    get_visible_journal_entries_for_user,
)
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.journal import make_journal_entry
from test_utils.users import make_admin, make_student, make_teacher


class JournalPermissionTests(TestCase):
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
        self.admin = make_admin('a@example.com')

    def test_student_views_own_entry(self):
        entry = make_journal_entry(self.student)
        self.assertTrue(can_view_journal_entry(self.student, entry))

    def test_teacher_views_shared(self):
        entry = make_journal_entry(
            self.student,
            visibility=JournalEntry.Visibility.SHARED,
        )
        self.assertTrue(can_view_journal_entry(self.teacher, entry))

    def test_teacher_not_private(self):
        entry = make_journal_entry(
            self.student,
            visibility=JournalEntry.Visibility.PRIVATE,
        )
        self.assertFalse(can_view_journal_entry(self.teacher, entry))

    def test_admin_can_delete_shared(self):
        entry = make_journal_entry(
            self.student,
            visibility=JournalEntry.Visibility.SHARED,
        )
        self.assertTrue(can_delete_journal_entry(self.admin, entry))

    def test_student_cannot_delete_others(self):
        other = make_student('o@example.com', cohort=self.cohort, group=self.group)
        entry = make_journal_entry(other, visibility=JournalEntry.Visibility.SHARED)
        self.assertFalse(can_delete_journal_entry(self.student, entry))

    def test_create_journal_student_only(self):
        self.assertTrue(can_create_journal_entries(self.student))
        self.assertFalse(can_create_journal_entries(self.teacher))

    def test_visible_for_student_own_only(self):
        make_journal_entry(self.student, title='Mine')
        other = make_student('o2@example.com', cohort=self.cohort, group=self.group)
        make_journal_entry(other, title='Other')
        titles = set(
            get_visible_journal_entries_for_user(self.student).values_list('title', flat=True)
        )
        self.assertEqual(titles, {'Mine'})
