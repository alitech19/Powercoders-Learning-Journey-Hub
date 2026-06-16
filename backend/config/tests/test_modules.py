from django.test import Client, TestCase, override_settings
from django.urls import reverse

from config.models import IntegratedModule
from config.module_access import invalidate_module_cache
from config.nav import integrated_nav_groups, metric_columns_for_request
from config.admin_menu import ADMIN_NAV_ITEMS, admin_nav_items
from test_utils.users import login_as, make_admin, make_student


@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class ModuleToggleTests(TestCase):
    def setUp(self):
        invalidate_module_cache()
        self.client = Client()

    def tearDown(self):
        invalidate_module_cache()

    def test_disabled_module_returns_stub_not_404(self):
        IntegratedModule.objects.filter(slug='tasks').update(is_enabled=False)
        invalidate_module_cache()
        student = make_student('student@test.com')
        login_as(self.client, student)
        response = self.client.get('/tasks/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tasks is not available')

    def test_admin_sees_enable_hint_on_stub(self):
        IntegratedModule.objects.filter(slug='tasks').update(is_enabled=False)
        invalidate_module_cache()
        admin = make_admin('admin@test.com')
        login_as(self.client, admin)
        response = self.client.get('/tasks/')
        self.assertContains(response, 'Integrated modules')

    def test_nav_hides_disabled_module(self):
        IntegratedModule.objects.filter(slug='tasks').update(is_enabled=False)
        invalidate_module_cache()
        groups = integrated_nav_groups()
        learning = next(g for g in groups if g['label'] == 'Learning')
        url_names = [c['url_name'] for c in learning['children']]
        self.assertNotIn('tasks:task_list', url_names)
        self.assertIn('goals:list', url_names)

    def test_nav_hides_empty_learning_group_when_all_off(self):
        for slug in ('workflows', 'tasks', 'goals', 'habits'):
            IntegratedModule.objects.filter(slug=slug).update(is_enabled=False)
        invalidate_module_cache()
        labels = [g['label'] for g in integrated_nav_groups()]
        self.assertNotIn('Learning', labels)

    def test_metric_columns_filter_disabled_modules(self):
        IntegratedModule.objects.filter(slug='resources').update(is_enabled=False)
        invalidate_module_cache()
        slugs = [slug for slug, _ in metric_columns_for_request()]
        self.assertNotIn('resources', slugs)
        self.assertIn('tasks', slugs)

    def test_admin_nav_matches_current_structure(self):
        admin = make_admin('admin-menu@test.com')
        labels = [item['label'] for item in admin_nav_items(user=admin)]
        self.assertEqual(
            labels,
            [
                'Cohorts & Groups',
                'Student Progress',
                'File storage',
                'Bug Reports',
                'Users',
                'Create User',
                'Import Users (CSV)',
                'Audit Log',
                'Django Admin',
            ],
        )
        self.assertEqual(len(ADMIN_NAV_ITEMS), 9)

    def test_admin_nav_hides_bug_reports_when_disabled(self):
        IntegratedModule.objects.filter(slug='bug_reports').update(is_enabled=False)
        invalidate_module_cache()
        admin = make_admin('admin2@test.com')
        labels = [item['label'] for item in admin_nav_items(user=admin)]
        self.assertNotIn('Bug Reports', labels)

    def test_module_disabled_named_route(self):
        response = self.client.get(reverse('module_disabled', kwargs={'slug': 'tasks'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tasks is not available')
