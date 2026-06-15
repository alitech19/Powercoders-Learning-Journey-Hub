"""Google storage access helpers."""

from accounts.models import User
from cohorts.permissions import user_is_admin

from .config import get_workspace_storage_config


def can_delete_drive_post(user, post) -> bool:
    """Drive-specific delete rules on top of group access."""
    from group_space.models import Post

    backend = getattr(post, 'drive_storage_backend', '') or ''
    if backend == Post.DriveStorageBackend.SHARED_ORG:
        return user_is_admin(user)
    if backend == Post.DriveStorageBackend.PERSONAL or post.drive_file_id:
        return user_is_admin(user) or post.author_id == user.pk
    return True


def can_retry_drive_upload(user, post) -> bool:
    from group_space.models import Post

    from .staging import has_staged_upload

    if not user.is_authenticated or post.author_id != user.pk:
        return False
    if post.drive_upload_status != Post.DriveUploadStatus.FAILED:
        return False
    return has_staged_upload(post.pk)


def student_google_connect_enabled(user) -> bool:
    if user.role != User.Role.STUDENT:
        return False
    config = get_workspace_storage_config()
    return config.student_uploads_enabled()


def staff_shared_drive_note_visible(user) -> bool:
    return user.role in (User.Role.TEACHER, User.Role.ADMIN)


def delete_drive_file_for_post(post) -> None:
    """Remove Drive file when post is deleted (admin paths only at call sites)."""
    from group_space.models import Post

    file_id = (post.drive_file_id or '').strip()
    if not file_id:
        return

    from .config import get_workspace_storage_config
    from .drive.oauth_client import build_user_drive_service
    from .drive.permissions_api import delete_drive_file as drive_delete
    from .drive.service_account import build_service_account_drive_service

    config = get_workspace_storage_config()
    if post.drive_storage_backend == Post.DriveStorageBackend.SHARED_ORG:
        service = build_service_account_drive_service(config.get_service_account_json())
        drive_delete(service, file_id, supports_all_drives=True)
        return

    if post.drive_storage_backend == Post.DriveStorageBackend.PERSONAL:
        connection = post.author.google_account_connection
        service = build_user_drive_service(connection, config)
        drive_delete(service, file_id)
