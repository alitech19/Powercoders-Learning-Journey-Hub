from django.core.exceptions import ValidationError
from django.test import TestCase

from tasks.models import Subtask, SubtaskEnrollment, Task, TaskEnrollment
from tasks.services import (
    AssigneeType,
    create_student_task,
    normalize_subtask_title,
    parse_subtasks_from_post,
    set_subtask_status,
    sync_subtask_enrollments,
    sync_subtasks,
)
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.tasks import enroll_student, make_personal_task
from test_utils.users import make_student, make_teacher


class TaskServicesTests(TestCase):
    def setUp(self):
        self.student = make_student('student@example.com')

    def test_normalize_subtask_title_unwraps_dict_string(self):
        self.assertEqual(normalize_subtask_title("{'title': 'Fix bug'}"), 'Fix bug')

    def test_parse_subtasks_from_post_legacy_title_only(self):
        post = {'st_1': 'A', 'st_2': 'B'}
        items = parse_subtasks_from_post(post)
        self.assertEqual([i['title'] for i in items], ['A', 'B'])

    def test_parse_subtasks_from_post_with_metadata(self):
        post = {
            'st_0_title': 'Read docs',
            'st_0_priority': 'high',
            'st_0_due_date': '2026-12-01',
        }
        items = parse_subtasks_from_post(post)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Read docs')
        self.assertEqual(items[0]['priority'], Task.Priority.HIGH)
        self.assertEqual(items[0]['due_date'], '2026-12-01')

    def test_parse_subtasks_with_description(self):
        post = {
            'st_0_title': 'Read chapter',
            'st_0_description': 'Sections 1-3',
            'st_0_priority': 'normal',
        }
        items = parse_subtasks_from_post(post)
        self.assertEqual(items[0]['description'], 'Sections 1-3')

    def test_sync_subtasks_updates_template_metadata(self):
        task = make_personal_task(self.student, title='T')
        Subtask.objects.create(task=task, title='Old', order=0)

        class PostDict(dict):
            def getlist(self, key):
                return super().get(key, [])

        sync_subtasks(
            task,
            PostDict({
                'st_0_title': 'New only',
                'st_0_description': 'With notes',
                'st_0_priority': 'low',
                'st_0_due_date': '2026-06-10',
            }),
        )
        subtask = task.subtasks.get(added_by__isnull=True)
        self.assertEqual(subtask.title, 'New only')
        self.assertEqual(subtask.description, 'With notes')
        self.assertEqual(subtask.priority, Task.Priority.LOW)
        self.assertEqual(str(subtask.due_date), '2026-06-10')

    def test_create_student_task_requires_title(self):
        class EmptyPost(dict):
            def getlist(self, key):
                return []

        with self.assertRaises(ValidationError):
            create_student_task(user=self.student, post=EmptyPost({}))

    def test_set_subtask_status(self):
        task = make_personal_task(self.student)
        enrollment = enroll_student(task, self.student)
        subtask = Subtask.objects.create(task=task, title='S1', order=0)
        sync_subtask_enrollments(enrollment)

        set_subtask_status(enrollment, subtask, Task.Status.DOING)
        row = SubtaskEnrollment.objects.get(enrollment=enrollment, subtask=subtask)
        self.assertEqual(row.status, Task.Status.DOING)

        set_subtask_status(enrollment, subtask, Task.Status.DONE)
        row.refresh_from_db()
        self.assertEqual(row.status, Task.Status.DONE)
        self.assertIsNotNone(row.completed_at)


class TaskBulkServicesTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            's@example.com',
            cohort=self.cohort,
            group=self.group,
        )

    def test_create_tasks_bulk(self):
        from tasks.services import create_tasks_bulk

        class Post(dict):
            def getlist(self, key):
                if key == 'student_ids':
                    return [str(self['student_ids'])]
                return super().get(key, [])

        task = create_tasks_bulk(
            user=self.teacher,
            post=Post(
                {
                    'title': 'Bulk task',
                    'assignee_type': AssigneeType.GROUP,
                    'assignee_target_id': str(self.group.pk),
                    'student_ids': str(self.student.pk),
                    'visibility': Task.Visibility.SHARED,
                    'st_0_title': 'Sub one',
                    'st_0_priority': 'normal',
                }
            ),
        )
        self.assertTrue(task.is_staff_assigned)
        enrollment = task.enrollments.get(student=self.student)
        self.assertEqual(task.subtasks.filter(added_by__isnull=True).count(), 1)
        self.assertEqual(enrollment.subtask_enrollments.count(), 1)
