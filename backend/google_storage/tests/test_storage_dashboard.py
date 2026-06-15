from django.test import TestCase

from google_storage.models import DriveUploadLog, GoogleAccountConnection
from google_storage.storage_dashboard import storage_dashboard_context
from test_utils.users import make_student


class StorageDashboardTests(TestCase):
    def test_empty_dashboard_context(self):
        ctx = storage_dashboard_context()
        self.assertEqual(ctx['upload_stats_7d']['success'], 0)
        self.assertEqual(list(ctx['student_connections']), [])
        self.assertEqual(list(ctx['recent_upload_logs']), [])

    def test_includes_active_connection(self):
        student = make_student('conn@example.com')
        GoogleAccountConnection.objects.create(
            user=student,
            google_subject='sub',
            google_email='conn@example.com',
        )
        ctx = storage_dashboard_context()
        self.assertEqual(len(list(ctx['student_connections'])), 1)
        self.assertEqual(ctx['student_connections'][0].google_email, 'conn@example.com')

    def test_upload_stats_counts_by_status(self):
        from group_space.models import Post
        from test_utils.cohorts import make_cohort, make_group
        from test_utils.group_space import get_space_for_group, make_post
        from test_utils.users import make_teacher

        group = make_group(make_cohort())
        space = get_space_for_group(group)
        teacher = make_teacher('stats@example.com')
        post = make_post(space, teacher, body='x')
        DriveUploadLog.objects.create(
            post=post,
            user=teacher,
            storage_backend=Post.DriveStorageBackend.SHARED_ORG,
            status=DriveUploadLog.Status.SUCCESS,
        )
        DriveUploadLog.objects.create(
            post=post,
            user=teacher,
            storage_backend=Post.DriveStorageBackend.SHARED_ORG,
            status=DriveUploadLog.Status.FAILED,
            error_message='boom',
        )
        ctx = storage_dashboard_context()
        self.assertEqual(ctx['upload_stats_7d']['success'], 1)
        self.assertEqual(ctx['upload_stats_7d']['failed'], 1)
