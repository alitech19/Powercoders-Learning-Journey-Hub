"""Student Google OAuth connect / disconnect."""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from google_auth_oauthlib.flow import Flow

from .config import get_workspace_storage_config
from .drive.oauth_client import (
    build_oauth_client_config,
    default_redirect_uri,
    fetch_google_email,
    oauth_scopes,
)
from .folders import PersonalDriveFolderService
from .models import GoogleAccountConnection


SESSION_STATE_KEY = 'google_oauth_state'


def _flow(config, *, redirect_uri: str) -> Flow:
    return Flow.from_client_config(
        build_oauth_client_config(config),
        scopes=oauth_scopes(),
        redirect_uri=redirect_uri,
        autogenerate_code_verifier=True,
    )


def start_connect(request):
    config = get_workspace_storage_config()
    if not config.student_uploads_enabled():
        messages.error(request, 'Student Google Drive uploads are not enabled.')
        return redirect('accounts:profile')

    redirect_uri = (config.oauth_redirect_uri or '').strip() or default_redirect_uri(request)
    flow = _flow(config, redirect_uri=redirect_uri)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
    )
    request.session[SESSION_STATE_KEY] = state
    request.session['google_oauth_code_verifier'] = flow.code_verifier
    request.session['google_oauth_redirect_uri'] = redirect_uri
    return redirect(authorization_url)


def finish_connect(request):
    config = get_workspace_storage_config()
    if not config.student_uploads_enabled():
        messages.error(request, 'Student Google Drive uploads are not enabled.')
        return redirect('accounts:profile')

    state = request.session.pop(SESSION_STATE_KEY, None)
    if not state or state != request.GET.get('state'):
        messages.error(request, 'Google sign-in expired. Please try again.')
        return redirect('accounts:profile')

    if request.GET.get('error'):
        messages.error(request, f"Google sign-in cancelled: {request.GET.get('error')}")
        return redirect('accounts:profile')

    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Google did not return an authorization code.')
        return redirect('accounts:profile')

    redirect_uri = request.session.pop('google_oauth_redirect_uri', '') or default_redirect_uri(request)
    code_verifier = request.session.pop('google_oauth_code_verifier', None)
    flow = _flow(config, redirect_uri=redirect_uri)
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    credentials = flow.credentials

    google_subject, google_email = fetch_google_email(credentials)
    user_email = request.user.email.strip().lower()
    if google_email != user_email:
        messages.error(
            request,
            f'Use your PowerHUB email ({user_email}) when signing in to Google.',
        )
        return redirect('accounts:profile')

    domain = (config.workspace_hosted_domain or '').strip().lower()
    if domain and not google_email.endswith(f'@{domain}'):
        messages.error(request, f'Use your @{domain} Google account.')
        return redirect('accounts:profile')

    connection, _created = GoogleAccountConnection.objects.update_or_create(
        user=request.user,
        defaults={
            'google_subject': google_subject,
            'google_email': google_email,
            'disconnected_at': None,
            'last_error': '',
        },
    )
    connection.set_tokens(
        access_token=credentials.token or '',
        refresh_token=credentials.refresh_token or connection.get_refresh_token(),
    )
    connection.token_expires_at = credentials.expiry
    connection.save()

    try:
        PersonalDriveFolderService(connection).ensure_root_folder()
    except Exception as exc:
        connection.last_error = str(exc)[:500]
        connection.save(update_fields=['last_error'])
        messages.warning(
            request,
            'Google connected, but creating your PowerHUB folder failed. Try reconnecting.',
        )
        return redirect('accounts:profile')

    messages.success(request, 'Google Drive connected successfully.')
    return redirect('accounts:profile')


def disconnect(request):
    try:
        connection = request.user.google_account_connection
    except GoogleAccountConnection.DoesNotExist:
        messages.info(request, 'No Google account is connected.')
        return redirect('accounts:profile')

    connection.mark_disconnected()
    messages.success(request, 'Google Drive disconnected.')
    return redirect('accounts:profile')
