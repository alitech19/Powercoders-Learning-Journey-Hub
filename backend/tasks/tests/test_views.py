from django.test import TestCase
from django.urls import reverse

from tasks.models import Subtask, SubtaskEnrollment, Task
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.tasks import (
    enroll_student,
    make_group_shared_task,
    make_personal_task,
    make_staff_individual_task,
)
from tasks.services import sync_subtask_enrollments
from test_utils.users import login_as, make_student, make_teacher


class TaskQuickStatusViewTests(TestCase):
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

    def _quick_status(self, user, task, *, status='doing', inline=False):
        login_as(self.client, user)
        url = reverse('tasks:task_quick_status', args=[task.pk])
        if inline:
            url = f'{url}?inline=list'
        return self.client.post(url, {'status': status})

    def test_enrolled_student_changes_status_on_list_inline(self):
        task = make_staff_individual_task(self.teacher, visibility=Task.Visibility.SHARED)
        enrollment = enroll_student(task, self.student, status=Task.Status.TODO)
        response = self._quick_status(self.student, task, status='doing', inline=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="task-status-')
        self.assertContains(response, 'border-blue-500')
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, Task.Status.DOING)

    def test_group_shared_student_changes_task_status_inline(self):
        task = make_group_shared_task(self.teacher, self.group, status=Task.Status.TODO)
        response = self._quick_status(self.student, task, status='done', inline=True)
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.DONE)

    def test_not_enrolled_student_cannot_change_status(self):
        task = make_staff_individual_task(self.teacher, visibility=Task.Visibility.SHARED)
        response = self._quick_status(self.student, task, status='doing', inline=True)
        self.assertIn(response.status_code, (403, 404))

    def test_detail_status_section_still_works(self):
        task = make_personal_task(self.student, visibility=Task.Visibility.PRIVATE)
        enroll_student(task, self.student)
        response = self._quick_status(self.student, task, status='doing', inline=False)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="task-status-section"')
        task.enrollments.get(student=self.student).refresh_from_db()
        self.assertEqual(
            task.enrollments.get(student=self.student).status,
            Task.Status.DOING,
        )


class TaskListStatusButtonsTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort, name='G1')
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
        )

    def test_student_list_shows_status_buttons_for_enrolled_task(self):
        task = make_staff_individual_task(self.teacher, title='Assigned', visibility=Task.Visibility.SHARED)
        enroll_student(task, self.student)
        login_as(self.client, self.student)
        response = self.client.get(reverse('tasks:task_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="task-status-{task.pk}"')
        self.assertContains(response, reverse('tasks:task_quick_status', args=[task.pk]) + '?inline=list')

    def test_student_list_badge_only_when_not_enrolled(self):
        task = make_staff_individual_task(self.teacher, title='Hidden', visibility=Task.Visibility.PRIVATE)
        login_as(self.client, self.student)
        response = self.client.get(reverse('tasks:task_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('tasks:task_quick_status', args=[task.pk]))

    def test_cohort_task_enrolled_student_has_list_buttons(self):
        task = Task.objects.create(
            author=None,
            created_by=self.teacher,
            assignee_type=Task.AssigneeType.USER,
            assignee_cohort=self.cohort,
            title='Cohort task',
            visibility=Task.Visibility.SHARED,
        )
        enroll_student(task, self.student)
        login_as(self.client, self.student)
        response = self.client.get(reverse('tasks:task_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'task-status-{task.pk}')
        self.assertContains(response, 'inline=list')


class SubtaskStatusViewTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort, name='G1')
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
        )

    def test_student_changes_subtask_status(self):
        task = make_staff_individual_task(self.teacher, visibility=Task.Visibility.SHARED)
        enrollment = enroll_student(task, self.student)
        subtask = Subtask.objects.create(task=task, title='Step 1', order=0, priority=Task.Priority.HIGH)
        sync_subtask_enrollments(enrollment)

        login_as(self.client, self.student)
        url = reverse('tasks:subtask_status', args=[subtask.pk])
        response = self.client.post(url, {'status': Task.Status.DOING})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="subtasks-section"')

        row = SubtaskEnrollment.objects.get(enrollment=enrollment, subtask=subtask)
        self.assertEqual(row.status, Task.Status.DOING)

    def test_subtask_detail_shows_status_buttons(self):
        task = make_staff_individual_task(self.teacher, visibility=Task.Visibility.SHARED)
        enrollment = enroll_student(task, self.student)
        subtask = Subtask.objects.create(task=task, title='Step 1', order=0)
        sync_subtask_enrollments(enrollment)

        login_as(self.client, self.student)
        response = self.client.get(reverse('tasks:task_detail', args=[task.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('tasks:subtask_status', args=[subtask.pk]))
        self.assertContains(response, 'Step 1')

    def test_student_edits_own_participant_subtask(self):
        task = make_staff_individual_task(self.teacher, visibility=Task.Visibility.SHARED)
        enrollment = enroll_student(task, self.student)
        subtask = Subtask.objects.create(
            task=task, title='Mine', order=0, added_by=self.student,
        )
        sync_subtask_enrollments(enrollment)

        login_as(self.client, self.student)
        url = reverse('tasks:subtask_edit', args=[subtask.pk])
        response = self.client.post(url, {
            'title': 'Updated mine',
            'description': 'More detail',
            'priority': Task.Priority.HIGH,
            'due_date': '',
        })
        self.assertEqual(response.status_code, 302)
        subtask.refresh_from_db()
        self.assertEqual(subtask.title, 'Updated mine')
        self.assertEqual(subtask.priority, Task.Priority.HIGH)
        self.assertEqual(subtask.description, 'More detail')

    def test_teacher_creates_template_subtask_with_description(self):
        task = make_staff_individual_task(self.teacher, visibility=Task.Visibility.SHARED)
        enroll_student(task, self.student)

        login_as(self.client, self.teacher)
        response = self.client.post(reverse('tasks:subtask_create', args=[task.pk]), {
            'title': 'Prepare slides',
            'description': 'Cover intro and demo',
            'priority': Task.Priority.NORMAL,
            'due_date': '',
        })
        self.assertEqual(response.status_code, 302)
        subtask = task.subtasks.get(title='Prepare slides')
        self.assertIsNone(subtask.added_by_id)
        self.assertEqual(subtask.description, 'Cover intro and demo')

    def test_student_deletes_own_participant_subtask(self):
        task = make_staff_individual_task(self.teacher, visibility=Task.Visibility.SHARED)
        enrollment = enroll_student(task, self.student)
        subtask = Subtask.objects.create(
            task=task, title='Remove me', order=0, added_by=self.student,
        )
        sync_subtask_enrollments(enrollment)

        login_as(self.client, self.student)
        url = reverse('tasks:subtask_delete', args=[subtask.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Subtask.objects.filter(pk=subtask.pk).exists())

    def test_student_cannot_delete_template_subtask(self):
        task = make_staff_individual_task(self.teacher, visibility=Task.Visibility.SHARED)
        enroll_student(task, self.student)
        subtask = Subtask.objects.create(task=task, title='Template', order=0)

        login_as(self.client, self.student)
        response = self.client.post(reverse('tasks:subtask_delete', args=[subtask.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Subtask.objects.filter(pk=subtask.pk).exists())

    def test_teacher_sees_subtasks_on_student_shared_personal_task(self):
        task = make_personal_task(self.student, visibility=Task.Visibility.SHARED)
        enrollment = enroll_student(task, self.student)
        subtask = Subtask.objects.create(
            task=task, title='Student step', order=0, added_by=self.student,
        )
        sync_subtask_enrollments(enrollment)

        login_as(self.client, self.teacher)
        response = self.client.get(reverse('tasks:task_detail', args=[task.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="subtasks-section"')
        self.assertContains(response, 'Student step')
        self.assertContains(response, '0/1 done')
