from unittest.mock import patch

from django.test import TestCase

from google_storage.models import GoogleWorkspaceStorageConfig
from google_storage.storage_admin import run_test_connection, validate_oauth_config


class StorageAdminActionTests(TestCase):
    def setUp(self):
        self.config = GoogleWorkspaceStorageConfig.objects.create(
            id=1,
            shared_drive_id='drive-1',
            oauth_client_id='client',
            oauth_redirect_uri='https://example.com/callback',
        )
        self.config.set_service_account_json('{"client_email":"sa@test.iam.gserviceaccount.com"}')
        self.config.set_oauth_client_secret('secret')
        self.config.save()

    @patch('google_storage.storage_admin.test_shared_drive_connection')
    def test_run_test_connection_records_success(self, mock_test):
        mock_test.return_value = {'ok': True, 'drive_name': 'PowerHUB Dev'}
        result = run_test_connection(self.config)
        self.config.refresh_from_db()
        self.assertTrue(result['ok'])
        self.assertTrue(self.config.last_health_ok)

    def test_validate_oauth_config(self):
        result = validate_oauth_config(self.config)
        self.assertTrue(result['ok'])
        self.assertIn('callback', result['redirect_uri'])
