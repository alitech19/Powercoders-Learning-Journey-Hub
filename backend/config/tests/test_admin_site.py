from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

User = get_user_model()


class AdminSiteGroupingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='pass',
            display_name='Admin',
        )

    def test_core_platform_groups_integrations_near_google(self):
        request = self.factory.get('/admin/')
        request.user = self.admin
        context = admin.site.each_context(request)
        core = next(s for s in context['powerhub_sections'] if s['title'] == 'Core Platform')
        names = [app['name'] for app in core['apps']]
        self.assertIn('Google Drive', names)
        self.assertIn('Notifications', names)
        self.assertIn('Slack', names)
        google_idx = names.index('Google Drive')
        notifications_idx = names.index('Notifications')
        slack_idx = names.index('Slack')
        accounts_idx = names.index('Accounts')
        self.assertLess(google_idx, notifications_idx)
        self.assertLess(notifications_idx, slack_idx)
        self.assertLess(slack_idx, accounts_idx)

    def test_slack_group_includes_workspace_config_and_channel_mappings(self):
        request = self.factory.get('/admin/')
        request.user = self.admin
        context = admin.site.each_context(request)
        core = next(s for s in context['powerhub_sections'] if s['title'] == 'Core Platform')
        slack = next(app for app in core['apps'] if app['name'] == 'Slack')
        model_names = {m['object_name'] for m in slack['models']}
        self.assertIn('SlackWorkspaceConfig', model_names)
        self.assertIn('SlackIntegration', model_names)
        self.assertIn('SpaceSlackChannel', model_names)
