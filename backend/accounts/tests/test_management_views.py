from django.test import TestCase
from django.urls import reverse

from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.users import login_as, make_admin, make_student, make_teacher


class ManagementViewAccessTests(TestCase):
    def setUp(self):
        self.admin = make_admin('admin@example.com')
        self.teacher = make_teacher('teacher@example.com')
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        assign_teacher(self.group, self.teacher)
        self.student = make_student('s@example.com', cohort=self.cohort, group=self.group)

    def test_admin_can_open_cohort_list(self):
        login_as(self.client, self.admin)
        response = self.client.get(reverse('accounts:cohort_list'))
        self.assertEqual(response.status_code, 200)

    def test_teacher_cannot_open_cohort_list(self):
        login_as(self.client, self.teacher)
        response = self.client.get(reverse('accounts:cohort_list'))
        self.assertEqual(response.status_code, 302)

    def test_teacher_can_open_student_progress(self):
        login_as(self.client, self.teacher)
        response = self.client.get(reverse('accounts:student_progress'))
        self.assertEqual(response.status_code, 200)

    def test_bulk_assign_students(self):
        other = make_student('other@example.com', cohort=self.cohort)
        login_as(self.client, self.admin)
        response = self.client.post(
            reverse('accounts:group_assign_students', args=[self.group.pk]),
            {'students': [str(other.pk)]},
        )
        self.assertEqual(response.status_code, 302)
        other.refresh_from_db()
        self.assertEqual(other.group_id, self.group.pk)
