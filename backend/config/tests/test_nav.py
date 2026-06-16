from django.test import TestCase

from config.admin_menu import admin_nav_items
from config.nav import NAV_GROUPS, NAV_REGISTRY, integrated_nav_groups, integrated_nav_items
from test_utils.users import make_admin


class NavRegistryTests(TestCase):
    def test_registry_order_matches_ui_plan(self):
        labels = [item.label for item in NAV_REGISTRY]
        self.assertEqual(
            labels,
            [
                'Workflows',
                'Tasks',
                'Goals',
                'Habits',
                'Reflections',
                'Journal',
                'Group Space',
                'Resources',
            ],
        )

    def test_four_nav_groups(self):
        self.assertEqual(len(NAV_GROUPS), 4)
        self.assertEqual(NAV_GROUPS[0].label, 'Learning')
        self.assertEqual(len(NAV_GROUPS[0].children), 4)

    def test_integrated_nav_groups_resolves_urls(self):
        groups = integrated_nav_groups(current_app='tasks')
        learning = next(g for g in groups if g['label'] == 'Learning')
        self.assertEqual(learning['label'], 'Learning')
        self.assertEqual(learning['kind'], 'dropdown')
        self.assertTrue(learning['active'])
        tasks = next(c for c in learning['children'] if c['url_name'] == 'tasks:task_list')
        self.assertTrue(tasks['active'])

    def test_group_space_link_group(self):
        groups = integrated_nav_groups(current_app='group_space')
        group_space = next(g for g in groups if g['label'] == 'Group Space')
        self.assertEqual(group_space['kind'], 'link')
        self.assertTrue(group_space['active'])

    def test_flat_items_backward_compat(self):
        items = integrated_nav_items(current_view_name='habits:list')
        habits = next(i for i in items if i['url_name'] == 'habits:list')
        self.assertTrue(habits['active'])

    def test_admin_nav_empty_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(admin_nav_items(user=AnonymousUser()), [])

    def test_admin_nav_labels_for_admin(self):
        admin = make_admin('nav-admin@test.com')
        labels = [i['label'] for i in admin_nav_items(user=admin)]
        self.assertIn('Django Admin', labels)
        self.assertIn('Cohorts & Groups', labels)
        self.assertIn('Users', labels)
        self.assertIn('Student Progress', labels)
