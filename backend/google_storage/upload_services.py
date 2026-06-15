"""Upload chat attachment bytes to Shared drive or student My Drive."""

from __future__ import annotations

import io
import mimetypes
from pathlib import Path

from googleapiclient.http import MediaIoBaseUpload

from .config import get_workspace_storage_config
from .drive.oauth_client import build_user_drive_service
from .drive.permissions_api import set_anyone_reader
from .drive.service_account import build_service_account_drive_service
from .folders import PersonalDriveFolderService, SharedDriveFolderService
from .models import GoogleAccountConnection, GoogleWorkspaceStorageConfig


def _guess_mime(filename: str, fallback: str) -> str:
    guessed, _encoding = mimetypes.guess_type(filename)
    return guessed or fallback or 'application/octet-stream'


def upload_to_shared_drive(
    *,
    group,
    filename: str,
    content: bytes,
    content_type: str = '',
    config: GoogleWorkspaceStorageConfig | None = None,
) -> dict:
    config = config or get_workspace_storage_config()
    folder = SharedDriveFolderService(config).ensure_group_folder(group)
    service = build_service_account_drive_service(config.get_service_account_json())
    media = MediaIoBaseUpload(
        io.BytesIO(content),
        mimetype=_guess_mime(filename, content_type),
        resumable=False,
    )
    created = (
        service.files()
        .create(
            body={
                'name': Path(filename).name,
                'parents': [folder.drive_folder_id],
            },
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True,
        )
        .execute()
    )
    set_anyone_reader(service, created['id'], supports_all_drives=True)
    return created


def upload_to_personal_drive(
    *,
    connection: GoogleAccountConnection,
    group,
    filename: str,
    content: bytes,
    content_type: str = '',
    config: GoogleWorkspaceStorageConfig | None = None,
) -> dict:
    config = config or get_workspace_storage_config()
    folder = PersonalDriveFolderService(connection).ensure_group_folder(group)
    service = build_user_drive_service(connection, config)
    media = MediaIoBaseUpload(
        io.BytesIO(content),
        mimetype=_guess_mime(filename, content_type),
        resumable=False,
    )
    created = (
        service.files()
        .create(
            body={
                'name': Path(filename).name,
                'parents': [folder.drive_folder_id],
            },
            media_body=media,
            fields='id, webViewLink',
        )
        .execute()
    )
    set_anyone_reader(service, created['id'])
    return created
