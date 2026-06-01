from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from feedback.models import FeedbackEntry
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.goals import enroll_student, make_staff_goal
from test_utils.users import confirm_totp_for_staff, login_as, make_student, make_teacher
from goals.models import Goal


class FeedbackViewTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
        )
        self.goal = make_staff_goal(self.teacher, visibility=Goal.Visibility.SHARED)
        self.enrollment = enroll_student(self.goal, self.student)
        self.ct = ContentType.objects.get_for_model(self.enrollment)
        confirm_totp_for_staff(self.teacher)

    def test_add_feedback_requires_login(self):
        url = reverse('feedback:add', args=[self.ct.pk, self.enrollment.pk])
        response = Client().post(url, {'body': 'Hi'})
        self.assertEqual(response.status_code, 302)

    def test_teacher_can_add_feedback(self):
        client = Client()
        login_as(client, self.teacher)
        url = reverse('feedback:add', args=[self.ct.pk, self.enrollment.pk])
        response = client.post(url, {'body': 'Well done'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FeedbackEntry.objects.count(), 1)

    def test_student_cannot_add_feedback(self):
        client = Client()
        login_as(client, self.student)
        url = reverse('feedback:add', args=[self.ct.pk, self.enrollment.pk])
        response = client.post(url, {'body': 'Self'})
        self.assertEqual(response.status_code, 403)

    def test_author_can_delete_feedback(self):
        client = Client()
        login_as(client, self.teacher)
        add_url = reverse('feedback:add', args=[self.ct.pk, self.enrollment.pk])
        client.post(add_url, {'body': 'Remove me'})
        entry = FeedbackEntry.objects.get()
        delete_url = reverse('feedback:delete', args=[entry.pk])
        response = client.post(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FeedbackEntry.objects.count(), 0)
