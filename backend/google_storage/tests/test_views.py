from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from google_storage.models import GoogleWorkspaceStorageConfig
from test_utils.users import login_as, make_admin, make_student, make_teacher


class StorageSettingsViewTests(TestCase):
    def setUp(self):
        self.admin = make_admin('admin-storage@example.com')
        self.teacher = make_teacher('teacher@example.com')
        self.url = reverse('accounts:storage_settings')

    def test_admin_can_open_storage_settings(self):
        login_as(self.client, self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'File storage')

    def test_teacher_redirected_from_storage_settings(self):
        login_as(self.client, self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    @patch('google_storage.views.run_test_connection')
    def test_test_connection_action(self, mock_test):
        mock_test.return_value = {'ok': True, 'drive_name': 'Test Drive'}
        login_as(self.client, self.admin)
        response = self.client.post(reverse('accounts:storage_test_connection'))
        self.assertEqual(response.status_code, 302)
        mock_test.assert_called_once()


class GoogleConnectViewTests(TestCase):
    def setUp(self):
        GoogleWorkspaceStorageConfig.objects.create(
            id=1,
            student_oauth_enabled=True,
            oauth_client_id='client-id',
        )
        config = GoogleWorkspaceStorageConfig.objects.get(id=1)
        config.set_oauth_client_secret('secret')
        config.save()
        self.student = make_student('student@powercoders.org')

    def test_student_connect_redirects_when_enabled(self):
        login_as(self.client, self.student)
        with patch('google_storage.oauth._flow') as mock_flow:
            flow = mock_flow.return_value
            flow.authorization_url.return_value = (
                'https://accounts.google.com/o/oauth2/auth?test=1',
                'state-token',
            )
            flow.code_verifier = 'test-code-verifier'
            response = self.client.get(reverse('accounts:google_connect'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('accounts.google.com', response.url)

    def test_teacher_cannot_connect(self):
        teacher = make_teacher('t@example.com')
        login_as(self.client, teacher)
        response = self.client.get(reverse('accounts:google_connect'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:profile'))


@override_settings(SITE_URL='http://testserver')
class ProfileGoogleSectionTests(TestCase):
    def test_profile_shows_connect_for_student(self):
        GoogleWorkspaceStorageConfig.objects.create(
            id=1,
            student_oauth_enabled=True,
            oauth_client_id='x',
        )
        config = GoogleWorkspaceStorageConfig.objects.get(id=1)
        config.set_oauth_client_secret('y')
        config.save()
        student = make_student('s@powercoders.org')
        login_as(self.client, student)
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, 'Connect Google Drive')

    def test_profile_shows_staff_note_for_teacher(self):
        GoogleWorkspaceStorageConfig.objects.create(id=1, is_enabled=True)
        teacher = make_teacher('t@example.com')
        login_as(self.client, teacher)
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, 'Shared drive')
