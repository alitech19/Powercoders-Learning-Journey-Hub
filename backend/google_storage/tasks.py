"""Celery tasks for Google Drive uploads."""

from __future__ import annotations

import logging
import time

from celery import shared_task
from group_space.models import Post

from .constants import DRIVE_UPLOAD_MAX_RETRIES, DRIVE_UPLOAD_RETRY_DELAY_SECONDS
from .models import DriveUploadLog
from .staging import delete_staged_upload, has_staged_upload, load_staged_upload
from .upload_services import upload_to_personal_drive, upload_to_shared_drive

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=DRIVE_UPLOAD_MAX_RETRIES,
    default_retry_delay=DRIVE_UPLOAD_RETRY_DELAY_SECONDS,
)
def upload_post_file_to_drive(self, post_id: int):
    started = time.monotonic()
    post = (
        Post.objects.select_related('author', 'group_space__group__cohort')
        .get(pk=post_id)
    )
    log = DriveUploadLog.objects.create(
        post=post,
        user=post.author,
        storage_backend=post.drive_storage_backend,
        status=DriveUploadLog.Status.PENDING,
    )

    try:
        content, meta = load_staged_upload(post_id)
        filename = meta.get('filename') or 'upload'
        content_type = meta.get('content_type') or 'application/octet-stream'

        if post.drive_storage_backend == Post.DriveStorageBackend.SHARED_ORG:
            created = upload_to_shared_drive(
                group=post.group_space.group,
                filename=filename,
                content=content,
                content_type=content_type,
            )
        else:
            connection = post.author.google_account_connection
            created = upload_to_personal_drive(
                connection=connection,
                group=post.group_space.group,
                filename=filename,
                content=content,
                content_type=content_type,
            )

        post.drive_file_id = created.get('id', '')
        post.drive_web_view_link = created.get('webViewLink', '')
        post.drive_upload_status = Post.DriveUploadStatus.READY
        post.drive_upload_error = ''
        post.save(
            update_fields=[
                'drive_file_id',
                'drive_web_view_link',
                'drive_upload_status',
                'drive_upload_error',
            ],
        )
        delete_staged_upload(post_id)

        from group_space.services import sync_group_resource_from_post

        sync_group_resource_from_post(post)

        duration_ms = int((time.monotonic() - started) * 1000)
        log.status = DriveUploadLog.Status.SUCCESS
        log.duration_ms = duration_ms
        log.save(update_fields=['status', 'duration_ms'])
        return post.drive_file_id

    except Exception as exc:
        logger.exception('Drive upload failed for post %s', post_id)
        post.drive_upload_status = Post.DriveUploadStatus.FAILED
        post.drive_upload_error = str(exc)[:500]
        post.save(update_fields=['drive_upload_status', 'drive_upload_error'])
        log.status = DriveUploadLog.Status.FAILED
        log.error_message = str(exc)[:500]
        log.duration_ms = int((time.monotonic() - started) * 1000)
        log.save(update_fields=['status', 'error_message', 'duration_ms'])
        if isinstance(exc, FileNotFoundError) or not has_staged_upload(post_id):
            return None
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return None
