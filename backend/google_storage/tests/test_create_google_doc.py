from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from google_storage.models import GoogleWorkspaceStorageConfig
from group_space.models import Post
from resources.models import ResourceItem
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.group_space import get_space_for_group
from test_utils.users import login_as, make_student, make_teacher


class GoogleDocCreateTests(TestCase):
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

    @patch('google_storage.create_services.create_google_file_on_shared_drive')
    def test_teacher_can_create_google_doc(self, mock_create):
        mock_create.return_value = {
            'id': 'doc-1',
            'webViewLink': 'https://docs.google.com/document/d/doc-1/edit',
        }
        teacher = make_teacher('teacher-doc@example.com')
        assign_teacher(self.group, teacher)
        login_as(self.client, teacher)
        response = self.client.post(
            reverse('group_space:google_doc_create'),
            {
                'group_pk': self.group.pk,
                'doc_kind': 'document',
                'resource_label': 'Week plan',
                'body': 'Here is our plan',
            },
        )
        self.assertEqual(response.status_code, 200)
        post = Post.objects.latest('pk')
        self.assertEqual(post.drive_doc_kind, 'document')
        self.assertEqual(post.drive_upload_status, Post.DriveUploadStatus.READY)
        self.assertEqual(post.resource_label, 'Week plan')
        self.assertEqual(post.body, 'Here is our plan')
        mock_create.assert_called_once()
        item = ResourceItem.objects.get(source_post=post)
        self.assertEqual(item.url, 'https://docs.google.com/document/d/doc-1/edit')

    @patch('google_storage.create_services.create_google_file_on_shared_drive')
    def test_spreadsheet_kind_passed_to_api(self, mock_create):
        mock_create.return_value = {
            'id': 'sheet-1',
            'webViewLink': 'https://docs.google.com/spreadsheets/d/sheet-1/edit',
        }
        teacher = make_teacher('teacher-sheet@example.com')
        assign_teacher(self.group, teacher)
        login_as(self.client, teacher)
        self.client.post(
            reverse('group_space:google_doc_create'),
            {
                'group_pk': self.group.pk,
                'doc_kind': 'spreadsheet',
                'resource_label': 'Tracker',
            },
        )
        post = Post.objects.latest('pk')
        self.assertEqual(post.drive_doc_kind, 'spreadsheet')
        mock_create.assert_called_once_with(
            group=self.group,
            name='Tracker',
            doc_kind='spreadsheet',
        )

    def test_student_without_google_gets_validation_error(self):
        student = make_student('student@example.com', group=self.group)
        login_as(self.client, student)
        response = self.client.post(
            reverse('group_space:google_doc_create'),
            {
                'group_pk': self.group.pk,
                'doc_kind': 'document',
                'resource_label': 'Notes',
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(Post.objects.filter(resource_label='Notes').exists())

    def test_resource_label_required(self):
        teacher = make_teacher('teacher-no-label@example.com')
        assign_teacher(self.group, teacher)
        login_as(self.client, teacher)
        response = self.client.post(
            reverse('group_space:google_doc_create'),
            {
                'group_pk': self.group.pk,
                'doc_kind': 'presentation',
                'resource_label': '',
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(Post.objects.exists())
