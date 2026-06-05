from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from config.page_meta import PAGE_PURPOSE, resolve_page_meta
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.users import login_as, make_student, make_teacher


class ResolvePageMetaTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, path, *, view_name):
        request = self.factory.get(path)
        request.resolver_match = type(
            'Match',
            (),
            {'view_name': view_name, 'url_name': view_name.split(':', 1)[-1]},
        )()
        request.user = type('Anon', (), {'is_authenticated': False})()
        return request

    def test_unknown_view_has_no_purpose(self):
        meta = resolve_page_meta(self._request('/x/', view_name='unknown:view'))
        self.assertFalse(meta['has_purpose'])
        self.assertEqual(meta['purpose'], '')

    def test_all_integrated_list_views_have_purpose(self):
        expected = {
            'workflows:list',
            'tasks:task_list',
            'goals:list',
            'habits:list',
            'reflections:list',
            'journal:list',
            'group_space:feed',
            'resources:index',
        }
        self.assertEqual(set(PAGE_PURPOSE.keys()), expected)


class PageMetaRoleTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.cohort = make_cohort()
        self.group = make_group(self.cohort, name='G1')
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
        )

    def _request(self, user, view_name):
        request = self.factory.get('/')
        request.user = user
        request.resolver_match = type(
            'Match',
            (),
            {'view_name': view_name, 'url_name': view_name.split(':', 1)[-1]},
        )()
        return request

    def test_student_gets_student_purpose_for_tasks(self):
        meta = resolve_page_meta(self._request(self.student, 'tasks:task_list'))
        self.assertTrue(meta['has_purpose'])
        self.assertIn('break tasks into subtasks', meta['purpose'])

    def test_teacher_gets_staff_purpose_for_tasks(self):
        meta = resolve_page_meta(self._request(self.teacher, 'tasks:task_list'))
        self.assertTrue(meta['has_purpose'])
        self.assertIn('See how students organize work', meta['purpose'])

    def test_resources_purpose_same_for_all_roles(self):
        student_meta = resolve_page_meta(self._request(self.student, 'resources:index'))
        teacher_meta = resolve_page_meta(self._request(self.teacher, 'resources:index'))
        self.assertEqual(student_meta['purpose'], teacher_meta['purpose'])
        self.assertIn('Curated link collections', student_meta['purpose'])


class PageMetaTemplateTests(TestCase):
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

    def test_task_list_shows_inline_purpose_and_help(self):
        login_as(self.client, self.student)
        response = self.client.get(reverse('tasks:task_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'break tasks into subtasks')
        self.assertContains(response, 'Help for')
        self.assertNotContains(response, 'pr-14')

    def test_task_list_create_button_on_list_card(self):
        login_as(self.client, self.student)
        response = self.client.get(reverse('tasks:task_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="list-card-header"')
        self.assertContains(response, 'New Task')
        self.assertContains(response, reverse('tasks:task_create'))

    def test_teacher_task_list_shows_staff_purpose(self):
        login_as(self.client, self.teacher)
        response = self.client.get(reverse('tasks:task_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'See how students organize work')

    def test_profile_shows_inline_help(self):
        login_as(self.client, self.student)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Help for Profile')
        self.assertContains(response, 'My Profile')

    def test_dashboard_shows_inline_help(self):
        login_as(self.client, self.student)
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Help for Dashboard')
