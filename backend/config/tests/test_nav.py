from django.test import SimpleTestCase

from config.nav import (
    ADMIN_NAV_ITEMS,
    NAV_GROUPS,
    NAV_REGISTRY,
    admin_nav_items,
    integrated_nav_groups,
    integrated_nav_items,
)


class NavRegistryTests(SimpleTestCase):
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
                'Чат',
                'Resources',
            ],
        )

    def test_four_nav_groups(self):
        self.assertEqual(len(NAV_GROUPS), 4)
        self.assertEqual(NAV_GROUPS[0].label, 'Learning')
        self.assertEqual(len(NAV_GROUPS[0].children), 4)

    def test_integrated_nav_groups_resolves_urls(self):
        groups = integrated_nav_groups(current_app='tasks')
        learning = groups[0]
        self.assertEqual(learning['label'], 'Learning')
        self.assertEqual(learning['kind'], 'dropdown')
        self.assertTrue(learning['active'])
        tasks = next(c for c in learning['children'] if c['url_name'] == 'tasks:task_list')
        self.assertTrue(tasks['active'])

    def test_chat_link_group(self):
        groups = integrated_nav_groups(current_app='group_space')
        chat = next(g for g in groups if g['label'] == 'Чат')
        self.assertEqual(chat['kind'], 'link')
        self.assertTrue(chat['active'])

    def test_flat_items_backward_compat(self):
        items = integrated_nav_items(current_view_name='habits:list')
        habits = next(i for i in items if i['url_name'] == 'habits:list')
        self.assertTrue(habits['active'])

    def test_admin_nav_empty_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(admin_nav_items(user=AnonymousUser()), [])

    def test_admin_nav_has_three_entries(self):
        from accounts.models import User

        admin = User(role=User.Role.ADMIN, email='a@test.com')
        items = admin_nav_items(user=admin)
        self.assertEqual(len(items), len(ADMIN_NAV_ITEMS))
