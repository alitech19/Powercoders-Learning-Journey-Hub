from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from google_storage.models import GoogleWorkspaceStorageConfig
from group_space.models import Post
from resources.models import ResourceItem
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.group_space import get_space_for_group
from test_utils.users import login_as, make_admin, make_student, make_teacher


class DriveChatUploadTests(TestCase):
    def setUp(self):
        self.group = make_group(make_cohort())
        self.space = get_space_for_group(self.group)
        config = GoogleWorkspaceStorageConfig.objects.create(
            id=1,
            is_enabled=True,
            shared_drive_id='drive-abc',
            student_oauth_enabled=True,
            oauth_client_id='client',
        )
        config.set_service_account_json('{"client_email":"sa@test.iam.gserviceaccount.com"}')
        config.set_oauth_client_secret('secret')
        config.save()

    @patch('google_storage.tasks.upload_to_shared_drive')
    def test_teacher_file_upload_uses_drive_not_local_file(self, mock_upload):
        mock_upload.return_value = {
            'id': 'file-123',
            'webViewLink': 'https://drive.google.com/file/d/file-123/view',
        }
        teacher = make_teacher('teacher-upload@example.com')
        assign_teacher(self.group, teacher)
        login_as(self.client, teacher)
        upload = SimpleUploadedFile(
            'notes.pdf',
            b'%PDF-1.4 test',
            content_type='application/pdf',
        )
        response = self.client.post(
            reverse('group_space:message_create'),
            {
                'group_pk': self.group.pk,
                'body': '',
                'resource_label': 'Week notes',
                'file': upload,
            },
        )
        self.assertEqual(response.status_code, 200)
        post = Post.objects.latest('pk')
        self.assertEqual(post.drive_upload_status, Post.DriveUploadStatus.READY)
        self.assertFalse(post.file)
        self.assertEqual(post.drive_storage_backend, Post.DriveStorageBackend.SHARED_ORG)
        mock_upload.assert_called_once()
        item = ResourceItem.objects.get(source_post=post)
        self.assertEqual(item.url, 'https://drive.google.com/file/d/file-123/view')
        self.assertEqual(item.storage_backend, ResourceItem.StorageBackend.GOOGLE_DRIVE_SHARED)

    def test_student_without_google_gets_validation_error(self):
        student = make_student('student@example.com', group=self.group)
        login_as(self.client, student)
        upload = SimpleUploadedFile('x.txt', b'hello', content_type='text/plain')
        response = self.client.post(
            reverse('group_space:message_create'),
            {
                'group_pk': self.group.pk,
                'resource_label': 'Doc',
                'file': upload,
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(Post.objects.filter(resource_label='Doc').exists())

    @patch('google_storage.permissions.user_is_admin', return_value=True)
    def test_teacher_cannot_delete_shared_org_post(self, _mock_admin):
        from test_utils.group_space import make_post

        teacher = make_teacher('t-del@example.com')
        admin = make_admin('admin-del@example.com')
        post = make_post(
            self.space,
            teacher,
            resource_label='Curriculum',
            body='',
        )
        post.drive_storage_backend = Post.DriveStorageBackend.SHARED_ORG
        post.drive_file_id = 'file-shared'
        post.drive_upload_status = Post.DriveUploadStatus.READY
        post.save()

        from group_space.permissions import can_delete_post

        self.assertFalse(can_delete_post(teacher, post))
        self.assertTrue(can_delete_post(admin, post))
