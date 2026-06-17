from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import SlackWorkspaceConfig
from accounts.slack_workspace_config import invalidate_slack_workspace_config, slack_oauth_configured
from test_utils.slack import clear_slack_workspace_config, configure_slack_oauth
from test_utils.users import login_as, make_admin, make_student, make_teacher


class SlackSettingsAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin('slack-admin@example.com')
        self.teacher = make_teacher('slack-teacher@example.com')

    def test_admin_can_open_slack_settings(self):
        login_as(self.client, self.admin)
        response = self.client.get(reverse('accounts:slack_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Slack integration')

    def test_teacher_cannot_open_slack_settings(self):
        login_as(self.client, self.teacher)
        response = self.client.get(reverse('accounts:slack_settings'))
        self.assertEqual(response.status_code, 302)


class SlackWorkspaceConfigTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin('slack-config@example.com')
        login_as(self.client, self.admin)
        clear_slack_workspace_config()

    def test_save_oauth_credentials_enables_connect_flow(self):
        response = self.client.post(
            reverse('accounts:slack_settings'),
            {
                'oauth_enabled': 'on',
                'oauth_client_id': 'test-client-id',
                'oauth_client_secret': 'test-client-secret',
                'oauth_redirect_uri': 'http://localhost:8000/accounts/slack/callback/',
                'webhook_enabled': '',
            },
        )
        self.assertRedirects(response, reverse('accounts:slack_settings'))
        invalidate_slack_workspace_config()
        self.assertTrue(slack_oauth_configured())
        config = SlackWorkspaceConfig.get()
        self.assertTrue(config.oauth_enabled)
        self.assertEqual(config.get_oauth_client_secret(), 'test-client-secret')

    def test_oauth_disabled_when_saved_off(self):
        config = SlackWorkspaceConfig.get()
        config.oauth_enabled = True
        config.oauth_client_id = 'id'
        config.set_oauth_client_secret('secret')
        config.save()
        invalidate_slack_workspace_config()

        self.client.post(
            reverse('accounts:slack_settings'),
            {
                'oauth_enabled': '',
                'oauth_client_id': 'id',
                'oauth_redirect_uri': 'http://localhost:8000/accounts/slack/callback/',
                'webhook_enabled': '',
            },
        )
        invalidate_slack_workspace_config()
        self.assertFalse(slack_oauth_configured())
