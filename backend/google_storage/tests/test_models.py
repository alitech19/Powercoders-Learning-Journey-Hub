import json

from django.test import TestCase

from google_storage.models import GoogleWorkspaceStorageConfig
from test_utils.users import make_admin


class GoogleWorkspaceStorageConfigTests(TestCase):
    def test_singleton_pk_forced_on_save(self):
        admin = make_admin('cfg@example.com')
        config = GoogleWorkspaceStorageConfig(id=99)
        sa_json = json.dumps({'client_email': 'sa@test.iam.gserviceaccount.com'})
        config.set_service_account_json(sa_json)
        config.updated_by = admin
        config.save()
        config.refresh_from_db()
        self.assertEqual(config.id, 1)
        self.assertEqual(config.service_account_email, 'sa@test.iam.gserviceaccount.com')

    def test_staff_uploads_enabled_requires_fields(self):
        config = GoogleWorkspaceStorageConfig.objects.create(id=1, is_enabled=True)
        self.assertFalse(config.staff_uploads_enabled())
        config.shared_drive_id = 'drive123'
        config.set_service_account_json('{"client_email":"x@y.z"}')
        config.save()
        self.assertTrue(config.staff_uploads_enabled())
