from django.core.exceptions import ValidationError
from django.test import TestCase

from tasks.models import Subtask, SubtaskCompletion, Task, TaskEnrollment
from tasks.services import (
    AssigneeType,
    create_student_task,
    normalize_subtask_title,
    parse_subtasks_from_post,
    sync_subtasks,
    toggle_subtask_completion,
)
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.tasks import enroll_student, make_personal_task
from test_utils.users import make_student, make_teacher


class TaskServicesTests(TestCase):
    def setUp(self):
        self.student = make_student('student@example.com')

    def test_normalize_subtask_title_unwraps_dict_string(self):
        self.assertEqual(normalize_subtask_title("{'title': 'Fix bug'}"), 'Fix bug')

    def test_parse_subtasks_from_post(self):
        post = {'st_1': 'A', 'st_2': 'B'}
        items = parse_subtasks_from_post(post)
        self.assertEqual([i['title'] for i in items], ['A', 'B'])

    def test_sync_subtasks_updates_template(self):
        task = make_personal_task(self.student, title='T')
        Subtask.objects.create(task=task, title='Old', order=0)

        class PostDict(dict):
            def getlist(self, key):
                return super().get(key, [])

        sync_subtasks(task, PostDict({'st_0': 'New only'}))
        titles = list(task.subtasks.filter(added_by__isnull=True).values_list('title', flat=True))
        self.assertEqual(titles, ['New only'])

    def test_create_student_task_requires_title(self):
        class EmptyPost(dict):
            def getlist(self, key):
                return []

        with self.assertRaises(ValidationError):
            create_student_task(user=self.student, post=EmptyPost({}))

    def test_toggle_subtask_completion(self):
        task = make_personal_task(self.student)
        enrollment = enroll_student(task, self.student)
        subtask = Subtask.objects.create(task=task, title='S1', order=0)
        self.assertEqual(enrollment.subtask_completions.count(), 0)

        toggle_subtask_completion(enrollment, subtask)
        self.assertEqual(enrollment.subtask_completions.count(), 1)

        toggle_subtask_completion(enrollment, subtask)
        self.assertEqual(enrollment.subtask_completions.count(), 0)


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
                    'st_0': 'Sub one',
                }
            ),
        )
        self.assertTrue(task.is_staff_assigned)
        self.assertEqual(task.enrollments.count(), 1)
        self.assertEqual(task.subtasks.filter(added_by__isnull=True).count(), 1)
