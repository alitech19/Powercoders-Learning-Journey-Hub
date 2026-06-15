"""Service account Google Drive client for org Shared drive operations."""

from __future__ import annotations

import json
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

DRIVE_SCOPES = ('https://www.googleapis.com/auth/drive',)


def build_service_account_drive_service(service_account_json: str):
    """Return an authenticated Drive API v3 client."""
    info = json.loads(service_account_json)
    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=DRIVE_SCOPES,
    )
    return build('drive', 'v3', credentials=credentials, cache_discovery=False)


def test_shared_drive_connection(*, service_account_json: str, shared_drive_id: str) -> dict[str, Any]:
    """
    Verify service account credentials and Shared drive access.
    Returns {'ok': True, 'drive_name': ...} or raises ValueError with a user-safe message.
    """
    if not service_account_json.strip():
        raise ValueError('Service account JSON is not configured.')
    if not shared_drive_id.strip():
        raise ValueError('Shared drive ID is not configured.')

    try:
        service = build_service_account_drive_service(service_account_json)
        drive = (
            service.drives()
            .get(driveId=shared_drive_id, supportsAllDrives=True)
            .execute()
        )
    except json.JSONDecodeError as exc:
        raise ValueError('Service account JSON is not valid JSON.') from exc
    except HttpError as exc:
        raise ValueError(f'Drive API error: {exc}') from exc
    except Exception as exc:
        raise ValueError(f'Connection failed: {exc}') from exc

    return {
        'ok': True,
        'drive_name': drive.get('name', ''),
        'drive_id': drive.get('id', shared_drive_id),
    }


def find_child_folder(
    service,
    *,
    parent_id: str,
    name: str,
    drive_id: str | None = None,
) -> str | None:
    """Return folder id if a child folder with `name` exists under parent_id."""
    q_parts = [
        f"'{parent_id}' in parents",
        f"name = '{name.replace(chr(39), '')}'",
        "mimeType = 'application/vnd.google-apps.folder'",
        'trashed = false',
    ]
    query = ' and '.join(q_parts)
    kwargs: dict[str, Any] = {
        'q': query,
        'fields': 'files(id, name)',
        'supportsAllDrives': True,
        'includeItemsFromAllDrives': True,
        'pageSize': 1,
    }
    if drive_id:
        kwargs['corpora'] = 'drive'
        kwargs['driveId'] = drive_id

    result = service.files().list(**kwargs).execute()
    files = result.get('files', [])
    if not files:
        return None
    return files[0]['id']


def create_folder(
    service,
    *,
    name: str,
    parent_id: str,
    drive_id: str | None = None,
) -> str:
    """Create a folder under parent_id; return new folder id."""
    metadata: dict[str, Any] = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id],
    }
    kwargs: dict[str, Any] = {
        'body': metadata,
        'fields': 'id',
        'supportsAllDrives': True,
    }
    created = service.files().create(**kwargs).execute()
    return created['id']
