from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from google_storage.models import GoogleWorkspaceStorageConfig
from google_storage.models import GoogleAccountConnection
from test_utils.users import make_student


@override_settings(SITE_URL='http://localhost:8000')
class GoogleOAuthCallbackTests(TestCase):
    def setUp(self):
        config = GoogleWorkspaceStorageConfig.objects.create(
            id=1,
            student_oauth_enabled=True,
            oauth_client_id='client-id',
            oauth_redirect_uri='http://localhost:8000/accounts/google/callback/',
        )
        config.set_oauth_client_secret('secret')
        config.save()
        self.student = make_student('student@example.com')

    def _session_with_state(self, client):
        session = client.session
        session['google_oauth_state'] = 'state-abc'
        session['google_oauth_code_verifier'] = 'verifier'
        session['google_oauth_redirect_uri'] = 'http://localhost:8000/accounts/google/callback/'
        session.save()

    @patch('google_storage.oauth._flow')
    def test_callback_rejects_missing_drive_scope(self, mock_flow_factory):
        login = self.client
        self.client.force_login(self.student)
        self._session_with_state(self.client)

        credentials = MagicMock()
        credentials.scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
        ]
        credentials.token = 'tok'
        credentials.refresh_token = 'ref'
        credentials.expiry = None

        flow = mock_flow_factory.return_value
        flow.credentials = credentials

        response = self.client.get(
            reverse('accounts:google_callback'),
            {'state': 'state-abc', 'code': 'auth-code'},
        )
        self.assertRedirects(response, reverse('accounts:profile'))
        self.assertFalse(GoogleAccountConnection.objects.filter(user=self.student).exists())

    @patch('google_storage.oauth.PersonalDriveFolderService')
    @patch('google_storage.oauth.fetch_google_email')
    @patch('google_storage.oauth._flow')
    def test_callback_succeeds_with_drive_scope(self, mock_flow_factory, mock_email, mock_folder):
        self.client.force_login(self.student)
        self._session_with_state(self.client)

        credentials = MagicMock()
        credentials.scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/drive.file',
        ]
        credentials.token = 'tok'
        credentials.refresh_token = 'ref'
        credentials.expiry = None

        flow = mock_flow_factory.return_value
        flow.credentials = credentials
        mock_email.return_value = ('sub-1', 'student@example.com')
        mock_folder.return_value.ensure_root_folder.return_value = MagicMock()

        response = self.client.get(
            reverse('accounts:google_callback'),
            {'state': 'state-abc', 'code': 'auth-code'},
        )
        self.assertRedirects(response, reverse('accounts:profile'))
        self.student.refresh_from_db()
        self.assertEqual(self.student.google_account_connection.google_email, 'student@example.com')
