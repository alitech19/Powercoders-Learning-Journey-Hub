"""Admin actions for workspace storage settings."""

from __future__ import annotations

from django.utils import timezone

from .config import get_workspace_storage_config
from .drive.service_account import test_shared_drive_connection
from .folders import SharedDriveFolderService
from .models import GoogleWorkspaceStorageConfig


def _record_health(config: GoogleWorkspaceStorageConfig, *, ok: bool, error: str = '') -> None:
    config.last_health_check_at = timezone.now()
    config.last_health_ok = ok
    config.last_error = error[:2000]
    config.save(update_fields=['last_health_check_at', 'last_health_ok', 'last_error', 'updated_at'])


def run_test_connection(config: GoogleWorkspaceStorageConfig | None = None) -> dict:
    config = config or get_workspace_storage_config()
    try:
        result = test_shared_drive_connection(
            service_account_json=config.get_service_account_json(),
            shared_drive_id=config.shared_drive_id,
        )
    except ValueError as exc:
        _record_health(config, ok=False, error=str(exc))
        raise
    _record_health(config, ok=True)
    return result


def run_ensure_root_folder(config: GoogleWorkspaceStorageConfig | None = None) -> str:
    config = config or get_workspace_storage_config()
    mapping = SharedDriveFolderService(config).ensure_root_folder()
    return mapping.drive_folder_id


def validate_oauth_config(config: GoogleWorkspaceStorageConfig | None = None) -> dict:
    config = config or get_workspace_storage_config()
    if not config.oauth_client_id:
        raise ValueError('OAuth client ID is not set.')
    if not config.oauth_client_secret_encrypted:
        raise ValueError('OAuth client secret is not set.')
    redirect = (config.oauth_redirect_uri or '').strip()
    if not redirect:
        raise ValueError('OAuth redirect URI is not set.')
    return {
        'ok': True,
        'redirect_uri': redirect,
        'client_id_suffix': config.oauth_client_id[-8:] if len(config.oauth_client_id) >= 8 else 'set',
    }
