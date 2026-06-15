"""OAuth-backed Google Drive client for student My Drive."""

from __future__ import annotations

from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from google_storage.models import GoogleAccountConnection, GoogleWorkspaceStorageConfig

DRIVE_FILE_SCOPE = 'https://www.googleapis.com/auth/drive.file'
OPENID_SCOPES = (
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    DRIVE_FILE_SCOPE,
)


def oauth_scopes() -> list[str]:
    return list(OPENID_SCOPES)


def default_redirect_uri(request) -> str:
    from django.conf import settings
    from django.urls import reverse

    base = settings.SITE_URL.rstrip('/')
    return f"{base}{reverse('accounts:google_callback')}"


def build_oauth_client_config(config: GoogleWorkspaceStorageConfig) -> dict:
    return {
        'web': {
            'client_id': config.oauth_client_id,
            'client_secret': config.get_oauth_client_secret(),
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': [config.oauth_redirect_uri],
        },
    }


def credentials_from_connection(
    connection: GoogleAccountConnection,
    config: GoogleWorkspaceStorageConfig,
) -> Credentials:
    return Credentials(
        token=connection.get_access_token() or None,
        refresh_token=connection.get_refresh_token() or None,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=config.oauth_client_id,
        client_secret=config.get_oauth_client_secret(),
        scopes=oauth_scopes(),
    )


def build_user_drive_service(
    connection: GoogleAccountConnection,
    config: GoogleWorkspaceStorageConfig,
):
    creds = credentials_from_connection(connection, config)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        connection.set_tokens(
            access_token=creds.token or '',
            refresh_token=creds.refresh_token or connection.get_refresh_token(),
        )
        connection.token_expires_at = creds.expiry
        connection.save(
            update_fields=['access_token_encrypted', 'refresh_token_encrypted', 'token_expires_at'],
        )
    return build('drive', 'v3', credentials=creds, cache_discovery=False)


def fetch_google_email(credentials: Credentials) -> tuple[str, str]:
    """Return (google_subject, email) from OAuth credentials."""
    oauth2 = build('oauth2', 'v2', credentials=credentials, cache_discovery=False)
    profile = oauth2.userinfo().get().execute()
    email = (profile.get('email') or '').strip().lower()
    subject = (profile.get('id') or profile.get('sub') or '').strip()
    if not email:
        raise ValueError('Google did not return an email address.')
    return subject, email
