from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase

from accounts.models import User
from info.content import load_topic, visible_sections
from info.registry import ADMIN_HELP_ROUTES, ROUTE_MAP, resolve_help_target, resolve_page_help


class AdministrationHelpRegistryTests(SimpleTestCase):
    def test_administration_routes_mapped(self):
        expected = {
            'accounts:cohort_list',
            'accounts:student_progress',
            'accounts:user_list',
            'accounts:user_import',
        }
        self.assertTrue(expected.issubset(ROUTE_MAP.keys()))
        for view_name in expected:
            app_slug, _section = ROUTE_MAP[view_name]
            self.assertEqual(app_slug, 'administration')

    def test_django_admin_audit_log_help_routes(self):
        self.assertIn('admin:index', ADMIN_HELP_ROUTES)
        self.assertIn('admin:accounts_auditlog_changelist', ADMIN_HELP_ROUTES)

    def test_resolve_help_for_student_progress(self):
        factory = RequestFactory()
        request = factory.get('/accounts/students/')
        request.user = User(role=User.Role.TEACHER, email='t@test.com')
        request.resolver_match = type(
            'M',
            (),
            {
                'view_name': 'accounts:student_progress',
                'url_name': 'student_progress',
                'namespace': 'accounts',
            },
        )()
        target = resolve_help_target(request)
        self.assertEqual(target, ('accounts.student_progress', 'administration', 'student-progress'))

    def test_resolve_help_for_audit_log_admin(self):
        factory = RequestFactory()
        request = factory.get('/admin/accounts/auditlog/')
        request.user = User(role=User.Role.ADMIN, email='a@test.com')
        request.resolver_match = type(
            'M',
            (),
            {
                'view_name': 'admin:accounts_auditlog_changelist',
                'url_name': 'accounts_auditlog_changelist',
                'namespace': 'admin',
            },
        )()
        target = resolve_help_target(request)
        self.assertEqual(
            target,
            ('admin.accounts_auditlog_changelist', 'administration', 'audit-log'),
        )

    def test_administration_topic_loads(self):
        topic = load_topic('administration')
        self.assertEqual(topic.app_slug, 'administration')
        section_ids = {s.section_id for s in topic.sections}
        self.assertIn('cohorts-groups', section_ids)
        self.assertIn('group-spaces', section_ids)
        self.assertIn('student-progress', section_ids)
        self.assertIn('import-users', section_ids)

    def test_teacher_sees_student_progress_not_cohorts_help(self):
        topic = load_topic('administration')
        teacher = User(role=User.Role.TEACHER, email='t@test.com')
        sections = visible_sections(topic, teacher)
        ids = {s.section_id for s in sections}
        self.assertIn('student-progress', ids)
        self.assertNotIn('cohorts-groups', ids)

    def test_resolve_help_for_notification_settings(self):
        factory = RequestFactory()
        request = factory.get('/accounts/notifications/settings/')
        request.user = User(role=User.Role.STUDENT, email='s@example.com')
        request.resolver_match = type(
            'M',
            (),
            {
                'view_name': 'accounts:notification_settings',
                'url_name': 'notification_settings',
                'namespace': 'accounts',
            },
        )()
        target = resolve_help_target(request)
        self.assertEqual(
            target,
            ('accounts.notification_settings', 'accounts', 'notification-settings'),
        )
        help_meta = resolve_page_help(request)
        self.assertTrue(help_meta.enabled)
        self.assertIn('notification-settings', help_meta.url)

    def test_accounts_topic_has_notification_settings_section(self):
        topic = load_topic('accounts')
        section_ids = {s.section_id for s in topic.sections}
        self.assertIn('notification-settings', section_ids)
        self.assertIn('notifications', section_ids)

    def test_slack_integration_topic_loads(self):
        topic = load_topic('slack_integration')
        self.assertEqual(topic.app_slug, 'slack_integration')
        section_ids = {s.section_id for s in topic.sections}
        self.assertIn('personal-oauth', section_ids)
        self.assertIn('staff-webhook', section_ids)

    def test_group_spaces_admin_routes_mapped(self):
        self.assertEqual(
            ROUTE_MAP['group_space:project_list'],
            ('group_spaces_admin', 'overview'),
        )
        self.assertEqual(
            ROUTE_MAP['group_space:project_create'],
            ('group_spaces_admin', 'create'),
        )

    def test_group_spaces_admin_topic_loads(self):
        topic = load_topic('group_spaces_admin')
        self.assertEqual(topic.app_slug, 'group_spaces_admin')
        section_ids = {s.section_id for s in topic.sections}
        self.assertIn('overview', section_ids)
        self.assertIn('archive', section_ids)

    def test_group_space_topic_has_space_types_section(self):
        topic = load_topic('group_space')
        section_ids = {s.section_id for s in topic.sections}
        self.assertIn('space-types', section_ids)
        self.assertIn('switching', section_ids)

    def test_resolve_help_for_group_spaces_list(self):
        factory = RequestFactory()
        request = factory.get('/group/projects/')
        request.user = User(role=User.Role.ADMIN, email='a@test.com')
        request.resolver_match = type(
            'M',
            (),
            {
                'view_name': 'group_space:project_list',
                'url_name': 'project_list',
                'namespace': 'group_space',
            },
        )()
        target = resolve_help_target(request)
        self.assertEqual(
            target,
            ('group_space.project_list', 'group_spaces_admin', 'overview'),
        )
        help_meta = resolve_page_help(request)
        self.assertTrue(help_meta.enabled)
        self.assertIn('group_spaces_admin', help_meta.url)

    def test_anonymous_page_help_disabled(self):
        factory = RequestFactory()
        request = factory.get('/accounts/cohorts/')
        request.user = AnonymousUser()
        self.assertFalse(resolve_page_help(request).enabled)
