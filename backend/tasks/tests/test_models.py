from django.core.exceptions import ValidationError
from django.test import TestCase

from tasks.models import Task
from test_utils.cohorts import make_cohort, make_group
from test_utils.tasks import make_group_shared_task, make_personal_task
from test_utils.users import make_student, make_teacher


class TaskModelTests(TestCase):
    def test_personal_task_str(self):
        student = make_student('s@example.com', display_name='Sam')
        task = make_personal_task(student, title='Homework')
        self.assertIn('Sam', str(task))
        self.assertIn('Homework', str(task))
        self.assertFalse(task.is_staff_assigned)

    def test_group_shared_task_sets_progress_mode_on_save(self):
        teacher = make_teacher('t@example.com')
        group = make_group(make_cohort())
        task = Task(
            author=None,
            created_by=teacher,
            assignee_type=Task.AssigneeType.GROUP,
            assignee_group=group,
            progress_mode=Task.ProgressMode.INDIVIDUAL,
            title='Bad',
            visibility=Task.Visibility.SHARED,
        )
        task.save()
        self.assertEqual(task.progress_mode, Task.ProgressMode.SHARED)
        self.assertTrue(task.is_group_shared)
        self.assertEqual(task.list_kind, Task.ListKind.GROUP)

    def test_clean_requires_group_for_group_assignee(self):
        teacher = make_teacher('t@example.com')
        task = Task(
            author=None,
            created_by=teacher,
            assignee_type=Task.AssigneeType.GROUP,
            title='X',
            visibility=Task.Visibility.SHARED,
        )
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_group_shared_task_completed_at_when_done(self):
        teacher = make_teacher('t@example.com')
        group = make_group(make_cohort())
        task = make_group_shared_task(teacher, group, status=Task.Status.DONE)
        self.assertIsNotNone(task.completed_at)
