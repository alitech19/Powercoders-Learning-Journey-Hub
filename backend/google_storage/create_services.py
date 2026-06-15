"""Create empty Google Workspace files in group Drive folders."""

from __future__ import annotations

from .config import get_workspace_storage_config
from .doc_types import GOOGLE_DOC_TYPE_BY_KEY
from .drive.oauth_client import build_user_drive_service
from .drive.permissions_api import set_anyone_reader
from .drive.service_account import build_service_account_drive_service
from .folders import PersonalDriveFolderService, SharedDriveFolderService
from .models import GoogleAccountConnection, GoogleWorkspaceStorageConfig


def _create_native_file(
    *,
    service,
    folder_id: str,
    name: str,
    mime_type: str,
    supports_all_drives: bool = False,
) -> dict:
    kwargs = {
        'body': {
            'name': name,
            'mimeType': mime_type,
            'parents': [folder_id],
        },
        'fields': 'id, webViewLink',
    }
    if supports_all_drives:
        kwargs['supportsAllDrives'] = True
    created = service.files().create(**kwargs).execute()
    set_anyone_reader(service, created['id'], supports_all_drives=supports_all_drives)
    return created


def create_google_file_on_shared_drive(
    *,
    group,
    name: str,
    doc_kind: str,
    config: GoogleWorkspaceStorageConfig | None = None,
) -> dict:
    doc_type = GOOGLE_DOC_TYPE_BY_KEY[doc_kind]
    config = config or get_workspace_storage_config()
    folder = SharedDriveFolderService(config).ensure_group_folder(group)
    service = build_service_account_drive_service(config.get_service_account_json())
    return _create_native_file(
        service=service,
        folder_id=folder.drive_folder_id,
        name=name,
        mime_type=doc_type.mime_type,
        supports_all_drives=True,
    )


def create_google_file_on_personal_drive(
    *,
    connection: GoogleAccountConnection,
    group,
    name: str,
    doc_kind: str,
    config: GoogleWorkspaceStorageConfig | None = None,
) -> dict:
    doc_type = GOOGLE_DOC_TYPE_BY_KEY[doc_kind]
    config = config or get_workspace_storage_config()
    folder = PersonalDriveFolderService(connection).ensure_group_folder(group)
    service = build_user_drive_service(connection, config)
    return _create_native_file(
        service=service,
        folder_id=folder.drive_folder_id,
        name=name,
        mime_type=doc_type.mime_type,
    )
