from unittest.mock import MagicMock, patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import NotificationDeliveryLog, SlackIntegration
from accounts.notifications.constants import EventType
from accounts.notifications.dispatcher import dispatch_event
from accounts.notifications.settings import get_notification_settings
from accounts.slack_provider import SlackApiError, build_authorize_url, exchange_oauth_code
from test_utils.users import login_as, make_student


@override_settings(
    SLACK_CLIENT_ID='test-client-id',
    SLACK_CLIENT_SECRET='test-client-secret',
    SITE_URL='http://testserver',
)
class SlackOAuthViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_student('slack-oauth@example.com')
        login_as(self.client, self.user)

    def test_connect_redirects_to_slack(self):
        response = self.client.get(reverse('accounts:slack_connect'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('slack.com/oauth/v2/authorize', response['Location'])
        self.assertIn('test-client-id', response['Location'])

    @patch('accounts.slack_oauth.exchange_oauth_code')
    def test_callback_creates_integration(self, mock_exchange):
        mock_exchange.return_value = {
            'access_token': 'xoxp-test-token',
            'slack_user_id': 'U123',
            'slack_team_id': 'T123',
        }
        session = self.client.session
        session['slack_oauth_state'] = 'state-123'
        session['slack_oauth_redirect_uri'] = 'http://testserver/accounts/slack/callback/'
        session.save()

        response = self.client.get(
            reverse('accounts:slack_callback'),
            {'state': 'state-123', 'code': 'oauth-code'},
        )
        self.assertRedirects(response, reverse('accounts:notification_settings'))
        integration = SlackIntegration.objects.get(user=self.user)
        self.assertTrue(integration.is_connected)
        self.assertEqual(integration.slack_user_id, 'U123')
        self.assertTrue(get_notification_settings(self.user).slack_enabled)

    @patch('accounts.slack_oauth.revoke_access_token')
    def test_disconnect_marks_integration_inactive(self, mock_revoke):
        integration = SlackIntegration.objects.create(
            user=self.user,
            slack_user_id='U123',
            slack_team_id='T123',
        )
        integration.set_access_token('xoxp-test-token')
        integration.save()

        response = self.client.post(reverse('accounts:slack_disconnect'))
        self.assertRedirects(response, reverse('accounts:notification_settings'))
        integration.refresh_from_db()
        self.assertFalse(integration.is_connected)
        mock_revoke.assert_called_once()


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SlackDispatcherTests(TestCase):
    def setUp(self):
        self.student = make_student('slack-dm@example.com', email_notifications_enabled=False)

    @patch('accounts.slack_provider.send_user_dm', return_value='1234.5678')
    def test_dispatch_sends_slack_dm_when_connected(self, mock_send):
        settings = get_notification_settings(self.student)
        settings.slack_enabled = True
        settings.save(update_fields=['slack_enabled'])

        integration = SlackIntegration.objects.create(
            user=self.student,
            slack_user_id='U999',
            slack_team_id='T999',
        )
        integration.set_access_token('xoxp-token')
        integration.save()

        dispatch_event(
            event_type=EventType.FEEDBACK,
            recipients=[self.student],
            title='Feedback',
            body='Nice work',
            url='/journal/1/',
            dedupe_key='feedback:slack-1',
            slack_text='Feedback arrived',
        )

        mock_send.assert_called_once()
        log = NotificationDeliveryLog.objects.get(
            recipient=self.student,
            channel=NotificationDeliveryLog.Channel.SLACK,
        )
        self.assertEqual(log.status, NotificationDeliveryLog.Status.SENT)

    def test_dispatch_skips_slack_when_not_connected(self):
        settings = get_notification_settings(self.student)
        settings.slack_enabled = True
        settings.save(update_fields=['slack_enabled'])

        dispatch_event(
            event_type=EventType.FEEDBACK,
            recipients=[self.student],
            title='Feedback',
            body='Nice work',
            url='/journal/1/',
            dedupe_key='feedback:slack-2',
            slack_text='Feedback arrived',
        )

        log = NotificationDeliveryLog.objects.get(
            recipient=self.student,
            channel=NotificationDeliveryLog.Channel.SLACK,
        )
        self.assertEqual(log.status, NotificationDeliveryLog.Status.SKIPPED)


class SlackProviderTests(TestCase):
    @override_settings(SLACK_CLIENT_ID='client', SLACK_CLIENT_SECRET='secret')
    def test_build_authorize_url_contains_user_scope(self):
        url = build_authorize_url(
            state='abc',
            redirect_uri='http://testserver/accounts/slack/callback/',
        )
        self.assertIn('user_scope=chat%3Awrite%2Cim%3Awrite', url)

    @override_settings(SLACK_CLIENT_ID='client', SLACK_CLIENT_SECRET='secret')
    @patch('urllib.request.urlopen')
    def test_exchange_oauth_code_parses_user_token(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = (
            b'{"ok": true, "authed_user": {"id": "U1", "access_token": "xoxp-1"}, '
            b'"team": {"id": "T1"}}'
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response
        data = exchange_oauth_code(
            code='code',
            redirect_uri='http://testserver/accounts/slack/callback/',
        )
        self.assertEqual(data['slack_user_id'], 'U1')
        self.assertEqual(data['access_token'], 'xoxp-1')

    @patch('accounts.slack_provider._api_post')
    def test_send_user_dm_opens_conversation_and_posts(self, mock_api_post):
        mock_api_post.side_effect = [
            {'ok': True, 'channel': {'id': 'D123'}},
            {'ok': True, 'ts': '111.222'},
        ]
        from accounts.slack_provider import send_user_dm

        ts = send_user_dm(access_token='xoxp-1', slack_user_id='U1', text='Hello')
        self.assertEqual(ts, '111.222')
        self.assertEqual(mock_api_post.call_count, 2)
