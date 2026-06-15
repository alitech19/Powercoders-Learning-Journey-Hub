"""Enqueue chat file uploads to Google Drive."""

from __future__ import annotations

from accounts.models import User
from group_space.models import Post

from .integration import should_upload_file_to_drive
from .rate_limit import check_drive_upload_rate_limit
from .staging import has_staged_upload, save_staged_upload
from .tasks import upload_post_file_to_drive


def prepare_drive_upload(post: Post, user, uploaded_file) -> None:
    if user.role in (User.Role.TEACHER, User.Role.ADMIN):
        backend = Post.DriveStorageBackend.SHARED_ORG
    else:
        backend = Post.DriveStorageBackend.PERSONAL

    post.file = None
    post.drive_storage_backend = backend
    post.drive_upload_status = Post.DriveUploadStatus.PENDING
    post.drive_upload_error = ''
    post.drive_file_id = ''
    post.drive_web_view_link = ''
    post.save(
        update_fields=[
            'file',
            'drive_storage_backend',
            'drive_upload_status',
            'drive_upload_error',
            'drive_file_id',
            'drive_web_view_link',
        ],
    )
    check_drive_upload_rate_limit(user.pk)
    save_staged_upload(post.pk, uploaded_file)
    upload_post_file_to_drive.delay(post.pk)


def retry_failed_drive_upload(post: Post) -> bool:
    """Re-enqueue a failed upload when staged bytes are still on disk."""
    if post.drive_upload_status != Post.DriveUploadStatus.FAILED:
        return False
    if not has_staged_upload(post.pk):
        return False

    post.drive_upload_status = Post.DriveUploadStatus.PENDING
    post.drive_upload_error = ''
    post.save(update_fields=['drive_upload_status', 'drive_upload_error'])
    upload_post_file_to_drive.delay(post.pk)
    return True


def handle_post_file_attachment(post: Post, user, uploaded_file) -> bool:
    """
    Route file to Drive when configured. Returns True if handled (Drive path).
    Caller should skip saving uploaded bytes on Post.file.
    """
    if not uploaded_file or not should_upload_file_to_drive(user):
        return False
    prepare_drive_upload(post, user, uploaded_file)
    return True
