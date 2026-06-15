"""Helpers for group chat ↔ Google Drive integration."""

from accounts.models import User

from .config import get_workspace_storage_config
from .models import GoogleAccountConnection


def get_active_google_connection(user) -> GoogleAccountConnection | None:
    try:
        connection = user.google_account_connection
    except GoogleAccountConnection.DoesNotExist:
        return None
    if not connection.is_active:
        return None
    return connection


def staff_drive_uploads_enabled() -> bool:
    return get_workspace_storage_config().staff_uploads_enabled()


def student_drive_uploads_enabled() -> bool:
    return get_workspace_storage_config().student_uploads_enabled()


def should_upload_file_to_drive(user) -> bool:
    """True when a new chat file should go to Drive instead of Post.file."""
    if user.role in (User.Role.TEACHER, User.Role.ADMIN):
        return staff_drive_uploads_enabled()
    if user.role == User.Role.STUDENT:
        return student_drive_uploads_enabled() and get_active_google_connection(user) is not None
    return False


def student_must_connect_google_for_upload(user) -> bool:
    return (
        user.role == User.Role.STUDENT
        and student_drive_uploads_enabled()
        and get_active_google_connection(user) is None
    )


from .doc_types import GOOGLE_DOC_TYPES


def can_create_google_doc(user) -> bool:
    return should_upload_file_to_drive(user)


def composer_upload_context(user) -> dict:
    return {
        'drive_chat_upload_enabled': should_upload_file_to_drive(user)
        or student_must_connect_google_for_upload(user)
        or staff_drive_uploads_enabled(),
        'drive_student_connect_required': student_must_connect_google_for_upload(user),
        'drive_staff_path': user.role in (User.Role.TEACHER, User.Role.ADMIN)
        and staff_drive_uploads_enabled(),
        'can_create_google_doc': can_create_google_doc(user),
        'google_doc_types': GOOGLE_DOC_TYPES,
    }
