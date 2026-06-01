from django.test import TestCase

from goals.models import Goal
from group_space.models import Post
from group_space.snapshots import (
    _clean_html,
    build_goal_snapshot,
    build_habit_snapshot,
    build_journal_snapshot,
    build_share_menu,
    build_snapshot_for_object,
    build_task_snapshot,
    get_shareable_object,
    list_shareable_objects,
)
from habits.models import Habit
from journal.models import JournalEntry
from tasks.models import Task
from test_utils.cohorts import make_cohort, make_group
from test_utils.goals import add_milestone, make_student_goal
from test_utils.habits import make_habit
from test_utils.journal import make_journal_entry
from test_utils.tasks import enroll_student, make_personal_task
from test_utils.users import make_student, make_teacher


class SnapshotHtmlTests(TestCase):
    def test_clean_html_strips_unsafe_tags(self):
        cleaned = _clean_html('<script>alert(1)</script><p class="ok">Safe</p>')
        self.assertNotIn('<script>', cleaned)
        self.assertIn('<p', cleaned)
        self.assertIn('Safe', cleaned)


class SnapshotBuildTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.student = make_student('s@example.com', group=self.group)

    def test_build_journal_snapshot(self):
        entry = make_journal_entry(
            self.student,
            title='Week notes',
            visibility=JournalEntry.Visibility.SHARED,
        )
        kind, html, meta = build_journal_snapshot(entry)
        self.assertEqual(kind, Post.SnapshotKind.JOURNAL)
        self.assertIn('Week notes', html)
        self.assertEqual(meta['title'], 'Week notes')
        self.assertEqual(meta['kind_label'], 'Journal entry')
        self.assertEqual(meta['entry_date'], entry.entry_date.isoformat())

    def test_build_habit_snapshot(self):
        habit = make_habit(
            self.student,
            title='Morning run',
            visibility=Habit.Visibility.SHARED,
        )
        kind, html, meta = build_habit_snapshot(habit, self.student)
        self.assertEqual(kind, Post.SnapshotKind.HABIT)
        self.assertIn('Morning run', html)
        self.assertEqual(meta['title'], 'Morning run')
        self.assertEqual(meta['kind_label'], 'Habit')

    def test_build_goal_snapshot_includes_milestones(self):
        goal = make_student_goal(
            self.student,
            title='Learn Django',
            visibility=Goal.Visibility.SHARED,
        )
        add_milestone(goal, title='Models', order=1)
        enrollment = goal.enrollments.get()
        kind, html, meta = build_goal_snapshot(goal, enrollment)
        self.assertEqual(kind, Post.SnapshotKind.GOAL)
        self.assertIn('Learn Django', html)
        self.assertIn('Models', html)
        self.assertEqual(meta['status'], enrollment.status)

    def test_build_task_snapshot_includes_subtasks(self):
        task = make_personal_task(
            self.student,
            title='Deploy app',
            visibility=Task.Visibility.SHARED,
        )
        enrollment = enroll_student(task, self.student)
        from tasks.models import Subtask

        Subtask.objects.create(task=task, title='Build image', order=1)
        kind, html, meta = build_task_snapshot(task, enrollment)
        self.assertEqual(kind, Post.SnapshotKind.TASK)
        self.assertIn('Deploy app', html)
        self.assertIn('Build image', html)
        self.assertEqual(meta['status'], enrollment.status)


class SnapshotShareMenuTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.student = make_student('s@example.com', group=self.group)

    def test_build_share_menu_only_for_students(self):
        teacher = make_teacher('t@example.com')
        self.assertIsNone(build_share_menu(teacher))

    def test_share_menu_lists_shared_objects_only(self):
        shared = make_journal_entry(
            self.student,
            title='Shared entry',
            visibility=JournalEntry.Visibility.SHARED,
        )
        make_journal_entry(
            self.student,
            title='Private entry',
            visibility=JournalEntry.Visibility.PRIVATE,
        )
        menu = build_share_menu(self.student)
        journal_ids = [e.pk for e in menu['journal']]
        self.assertIn(shared.pk, journal_ids)
        self.assertEqual(len(journal_ids), 1)

    def test_list_shareable_objects_returns_kind_slice(self):
        entry = make_journal_entry(
            self.student,
            visibility=JournalEntry.Visibility.SHARED,
        )
        items = list_shareable_objects(self.student, Post.SnapshotKind.JOURNAL)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].pk, entry.pk)

    def test_get_shareable_object_denies_private_journal(self):
        entry = make_journal_entry(
            self.student,
            visibility=JournalEntry.Visibility.PRIVATE,
        )
        self.assertIsNone(
            get_shareable_object(self.student, Post.SnapshotKind.JOURNAL, entry.pk),
        )

    def test_get_shareable_object_returns_shared_goal(self):
        goal = make_student_goal(
            self.student,
            visibility=Goal.Visibility.SHARED,
        )
        found = get_shareable_object(self.student, Post.SnapshotKind.GOAL, goal.pk)
        self.assertEqual(found.pk, goal.pk)

    def test_get_shareable_object_invalid_kind(self):
        entry = make_journal_entry(
            self.student,
            visibility=JournalEntry.Visibility.SHARED,
        )
        self.assertIsNone(get_shareable_object(self.student, 'invalid', entry.pk))

    def test_build_snapshot_for_object_dispatches_by_type(self):
        entry = make_journal_entry(
            self.student,
            visibility=JournalEntry.Visibility.SHARED,
        )
        kind, html, meta = build_snapshot_for_object(self.student, entry)
        self.assertEqual(kind, Post.SnapshotKind.JOURNAL)
        self.assertIn(entry.title, html)
        self.assertEqual(meta['title'], entry.title)

    def test_build_snapshot_for_object_rejects_unknown_type(self):
        with self.assertRaises(TypeError):
            build_snapshot_for_object(self.student, self.group)
