from django.test import TestCase

from tasks.models import Task
from tasks.permissions import (
    can_change_status,
    can_view_task,
    can_view_task_content,
    get_visible_tasks_for_user,
    is_staff_assigned,
)
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.tasks import (
    enroll_student,
    make_group_shared_task,
    make_personal_task,
    make_staff_individual_task,
)
from test_utils.users import make_admin, make_student, make_teacher


class TaskPermissionTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort, name='G1')
        self.other_group = make_group(self.cohort, name='G2')
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
        )
        self.other_student = make_student(
            'other@example.com',
            cohort=self.cohort,
            group=self.other_group,
        )
        self.admin = make_admin('admin@example.com')

    def test_student_views_own_private_task(self):
        task = make_personal_task(self.student, visibility=Task.Visibility.PRIVATE)
        self.assertTrue(can_view_task(self.student, task))
        self.assertTrue(can_view_task_content(self.student, task))

    def test_teacher_cannot_view_private_student_task_content(self):
        task = make_personal_task(self.student, visibility=Task.Visibility.PRIVATE)
        self.assertTrue(can_view_task(self.teacher, task))
        self.assertFalse(can_view_task_content(self.teacher, task))

    def test_teacher_views_shared_student_task(self):
        task = make_personal_task(self.student, visibility=Task.Visibility.SHARED)
        self.assertTrue(can_view_task_content(self.teacher, task))

    def test_group_shared_task_student_in_group(self):
        task = make_group_shared_task(self.teacher, self.group)
        self.assertTrue(can_view_task_content(self.student, task))
        self.assertTrue(can_change_status(self.student, task))

    def test_group_shared_task_student_wrong_group(self):
        task = make_group_shared_task(self.teacher, self.other_group)
        self.assertFalse(can_view_task_content(self.student, task))

    def test_staff_individual_task_requires_enrollment(self):
        task = make_staff_individual_task(self.teacher, visibility=Task.Visibility.SHARED)
        self.assertFalse(can_view_task_content(self.student, task))
        enrollment = enroll_student(task, self.student)
        self.assertTrue(can_view_task_content(self.student, task))
        self.assertTrue(can_change_status(self.student, task, enrollment=enrollment))

    def test_teacher_manages_staff_task_in_scope(self):
        task = make_staff_individual_task(self.teacher, visibility=Task.Visibility.PRIVATE)
        enroll_student(task, self.student)
        self.assertTrue(is_staff_assigned(task))
        from tasks.permissions import can_manage_task

        self.assertTrue(can_manage_task(self.teacher, task))

    def test_visible_tasks_for_student_includes_enrolled_staff_task(self):
        task = make_staff_individual_task(self.teacher, title='Assigned', visibility=Task.Visibility.SHARED)
        enroll_student(task, self.student)
        other = make_staff_individual_task(self.teacher, title='Other', visibility=Task.Visibility.SHARED)
        enroll_student(other, self.other_student)
        titles = set(get_visible_tasks_for_user(self.student).values_list('title', flat=True))
        self.assertIn('Assigned', titles)
        self.assertNotIn('Other', titles)
