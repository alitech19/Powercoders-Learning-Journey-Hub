import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from google_storage.staging import (
    delete_staged_upload,
    has_staged_upload,
    load_staged_upload,
    save_staged_upload,
    staging_root,
)


class StagingTests(TestCase):
    def test_save_load_and_delete_staged_upload(self):
        upload = SimpleUploadedFile('notes.pdf', b'%PDF-1.4', content_type='application/pdf')
        save_staged_upload(42, upload)
        self.assertTrue(has_staged_upload(42))

        content, meta = load_staged_upload(42)
        self.assertEqual(content, b'%PDF-1.4')
        self.assertEqual(meta['filename'], 'notes.pdf')
        self.assertEqual(meta['content_type'], 'application/pdf')

        delete_staged_upload(42)
        self.assertFalse(has_staged_upload(42))

    @override_settings(
        GOOGLE_UPLOAD_STAGING_ROOT=Path(tempfile.mkdtemp(prefix='powerhub_staging_test_')),
    )
    def test_staging_root_uses_configured_directory(self):
        expected = Path(settings.GOOGLE_UPLOAD_STAGING_ROOT)
        self.assertEqual(staging_root().resolve(), expected.resolve())
