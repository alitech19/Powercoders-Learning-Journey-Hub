from django.test import Client, TestCase

from goals.models import Goal
from group_space.models import Post
from group_space.snapshots import (
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
from tasks.models import Subtask, Task
from test_utils.cohorts import make_cohort, make_group
from test_utils.group_space import get_space_for_group
from test_utils.goals import add_milestone, make_student_goal
from test_utils.habits import make_habit
from test_utils.journal import make_journal_entry
from test_utils.tasks import enroll_student, make_personal_task
from test_utils.users import make_student, make_teacher


class SnapshotBuildTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.student = make_student('s@example.com', group=self.group)

    def test_build_journal_snapshot_stores_json_not_html(self):
        entry = make_journal_entry(
            self.student,
            title='Week notes',
            visibility=JournalEntry.Visibility.SHARED,
        )
        kind, html, meta = build_journal_snapshot(entry)
        self.assertEqual(kind, Post.SnapshotKind.JOURNAL)
        self.assertEqual(html, '')
        self.assertEqual(meta['title'], 'Week notes')
        self.assertEqual(meta['kind'], Post.SnapshotKind.JOURNAL)
        self.assertEqual(meta['entry_date'], entry.entry_date.isoformat())

    def test_build_habit_snapshot(self):
        habit = make_habit(
            self.student,
            title='Morning run',
            visibility=Habit.Visibility.SHARED,
        )
        kind, html, meta = build_habit_snapshot(habit, self.student)
        self.assertEqual(kind, Post.SnapshotKind.HABIT)
        self.assertEqual(html, '')
        self.assertEqual(meta['title'], 'Morning run')
        self.assertIn('week_table', meta)

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
        self.assertEqual(html, '')
        self.assertEqual(meta['milestones_total'], 1)
        self.assertEqual(meta['milestones'][0]['title'], 'Models')

    def test_build_task_snapshot_includes_subtasks(self):
        task = make_personal_task(
            self.student,
            title='Deploy app',
            visibility=Task.Visibility.SHARED,
        )
        enrollment = enroll_student(task, self.student)
        Subtask.objects.create(task=task, title='Build image', order=1)
        kind, html, meta = build_task_snapshot(task, enrollment)
        self.assertEqual(kind, Post.SnapshotKind.TASK)
        self.assertEqual(html, '')
        self.assertEqual(meta['subtasks_total'], 1)
        self.assertEqual(meta['subtasks'][0]['title'], 'Build image')


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
        journal_ids = [entry.pk for entry in menu['journal']]
        self.assertIn(shared.pk, journal_ids)
        self.assertEqual(len(journal_ids), 1)

    def test_get_shareable_object_returns_shared_goal_via_enrollment(self):
        goal = make_student_goal(
            self.student,
            visibility=Goal.Visibility.SHARED,
        )
        found = get_shareable_object(self.student, Post.SnapshotKind.GOAL, goal.pk)
        self.assertEqual(found.pk, goal.pk)

    def test_build_snapshot_for_object_dispatches_by_type(self):
        entry = make_journal_entry(
            self.student,
            visibility=JournalEntry.Visibility.SHARED,
        )
        kind, html, meta = build_snapshot_for_object(self.student, entry)
        self.assertEqual(kind, Post.SnapshotKind.JOURNAL)
        self.assertEqual(html, '')
        self.assertEqual(meta['title'], entry.title)


class ShareCreateWithoutDriveTests(TestCase):
    def setUp(self):
        from google_storage.models import GoogleWorkspaceStorageConfig

        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.space = get_space_for_group(self.group)
        self.student = make_student('share@example.com', cohort=self.cohort, group=self.group)
        GoogleWorkspaceStorageConfig.objects.create(
            id=1,
            is_enabled=True,
            shared_drive_id='drive-abc',
            student_oauth_enabled=True,
            oauth_client_id='client',
        )

    def test_student_can_share_journal_without_google_connection(self):
        from django.urls import reverse

        from test_utils.journal import make_journal_entry
        from test_utils.users import login_as

        entry = make_journal_entry(
            self.student,
            title='Shared reflection',
            visibility=JournalEntry.Visibility.SHARED,
        )
        client = Client()
        login_as(client, self.student)
        response = client.post(
            reverse('group_space:share_create'),
            {
                'space_kind': 'cohort_group',
                'space_pk': self.group.pk,
                'kind': Post.SnapshotKind.JOURNAL,
                'obj_id': entry.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        post = Post.objects.latest('pk')
        self.assertEqual(post.snapshot_kind, Post.SnapshotKind.JOURNAL)
        self.assertEqual(post.snapshot_meta['title'], 'Shared reflection')
        self.assertFalse(post.drive_file_id)
