"""Automated pre-flight checks aligned with docs/USABILITY_TESTING.md scenarios."""

from django.test import TestCase
from django.urls import reverse

from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.users import login_as, make_student, make_teacher

STUDENT_HUB_URLS = [
    'dashboard:dashboard',
    'journal:list',
    'goals:list',
    'tasks:task_list',
    'reflections:list',
    'group_space:feed',
    'resources:index',
    'habits:list',
    'workflows:list',
]

TEACHER_HUB_URLS = STUDENT_HUB_URLS + [
    'accounts:student_progress',
]


class UsabilitySmokeTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort, name='G1')
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
            welcome_seen=True,
        )

    def test_student_core_pages_load(self):
        login_as(self.client, self.student)
        for url_name in STUDENT_HUB_URLS:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200, url_name)

    def test_teacher_core_pages_load(self):
        login_as(self.client, self.teacher)
        for url_name in TEACHER_HUB_URLS:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200, url_name)

    def test_nav_shows_learning_dropdown_and_group_space(self):
        login_as(self.client, self.student)
        response = self.client.get(reverse('dashboard:dashboard'))
        html = response.content.decode()
        self.assertIn('Learning', html)
        self.assertIn('Group Space', html)
        self.assertIn('Resources', html)

    def test_list_pages_show_purpose_subtitle(self):
        login_as(self.client, self.student)
        for url_name in (
            'tasks:task_list',
            'goals:list',
            'journal:list',
            'reflections:list',
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertContains(response, 'text-gray-500 text-sm')

    def test_student_welcome_tutorial_loads(self):
        self.student.welcome_seen = False
        self.student.save(update_fields=['welcome_seen'])
        login_as(self.client, self.student)
        response = self.client.get(reverse('accounts:welcome'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Show me around')
