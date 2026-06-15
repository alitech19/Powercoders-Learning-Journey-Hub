from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.models import User

from .config import get_workspace_storage_config
from .drive.oauth_client import default_redirect_uri
from .forms import WorkspaceStorageSettingsForm
from .models import GoogleAccountConnection, GoogleWorkspaceStorageConfig
from . import oauth as google_oauth
from .permissions import student_google_connect_enabled
from .storage_admin import run_ensure_root_folder, run_test_connection, validate_oauth_config
from .storage_dashboard import storage_dashboard_context


def _default_oauth_redirect(request) -> str:
    return default_redirect_uri(request)


@admin_required
def storage_settings(request):
    config, _created = GoogleWorkspaceStorageConfig.objects.get_or_create(id=1)
    if not config.oauth_redirect_uri:
        config.oauth_redirect_uri = _default_oauth_redirect(request)
        config.save(update_fields=['oauth_redirect_uri', 'updated_at'])

    if request.method == 'POST':
        form = WorkspaceStorageSettingsForm(request.POST, instance=config)
        if form.is_valid():
            instance = form.save(commit=False)
            form.save_secrets(instance)
            instance.updated_by = request.user
            instance.save()
            messages.success(request, 'Storage settings saved.')
            return redirect('accounts:storage_settings')
    else:
        form = WorkspaceStorageSettingsForm(instance=config)

    return render(
        request,
        'google_storage/storage_settings.html',
        {
            'form': form,
            'config': config,
            'suggested_redirect_uri': _default_oauth_redirect(request),
            'has_sa_json': bool(config.service_account_json_encrypted),
            'has_oauth_secret': bool(config.oauth_client_secret_encrypted),
            'masked_sa': config.masked_service_account_json,
            'masked_oauth_secret': config.masked_oauth_client_secret,
            **storage_dashboard_context(),
        },
    )


@admin_required
@require_POST
def storage_test_connection(request):
    config = get_workspace_storage_config()
    try:
        result = run_test_connection(config)
        messages.success(
            request,
            f"Connection OK — Shared drive “{result.get('drive_name', '')}”.",
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('accounts:storage_settings')


@admin_required
@require_POST
def storage_test_oauth(request):
    config = get_workspace_storage_config()
    try:
        result = validate_oauth_config(config)
        messages.success(
            request,
            f"OAuth config looks valid. Redirect URI: {result['redirect_uri']}",
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('accounts:storage_settings')


@admin_required
@require_POST
def storage_ensure_root(request):
    config = get_workspace_storage_config()
    try:
        folder_id = run_ensure_root_folder(config)
        messages.success(request, f'PowerHUB root folder ready (id: {folder_id}).')
    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception as exc:
        messages.error(request, f'Could not ensure root folder: {exc}')
    return redirect('accounts:storage_settings')


@login_required
def google_connect(request):
    if request.user.role != User.Role.STUDENT:
        messages.error(request, 'Only students connect a personal Google Drive account.')
        return redirect('accounts:profile')
    if not student_google_connect_enabled(request.user):
        messages.error(request, 'Google Drive student uploads are not enabled yet.')
        return redirect('accounts:profile')
    return google_oauth.start_connect(request)


@login_required
def google_callback(request):
    if request.user.role != User.Role.STUDENT:
        return redirect('accounts:profile')
    return google_oauth.finish_connect(request)


@login_required
@require_POST
def google_disconnect(request):
    return google_oauth.disconnect(request)


def profile_google_context(user) -> dict:
    """Context for profile Google Drive section."""
    config = get_workspace_storage_config()
    connection = None
    if user.is_authenticated:
        connection = GoogleAccountConnection.objects.filter(user=user).first()

    return {
        'google_storage_config': config,
        'google_connection': connection,
        'google_connect_enabled': student_google_connect_enabled(user),
        'google_staff_storage_note': user.role in (User.Role.TEACHER, User.Role.ADMIN),
        'google_callback_url': f"{settings.SITE_URL.rstrip('/')}{reverse('accounts:google_callback')}",
    }
