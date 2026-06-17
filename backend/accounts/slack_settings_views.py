from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.models import SlackWorkspaceConfig
from accounts.slack import send_slack_message
from accounts.slack_provider import default_redirect_uri, post_channel_message, slack_oauth_configured, SlackApiError
from accounts.slack_settings_forms import SlackWorkspaceSettingsForm
from accounts.slack_workspace_config import (
    chat_sync_configured,
    get_slack_workspace_config,
    invalidate_slack_workspace_config,
    resolve_bot_token,
    resolve_oauth_client_id,
    resolve_oauth_redirect_uri,
    staff_webhook_configured,
)


def _suggested_redirect_uri(request) -> str:
    return default_redirect_uri(request)


@admin_required
def slack_settings(request):
    config = SlackWorkspaceConfig.get()
    if not config.oauth_redirect_uri:
        config.oauth_redirect_uri = _suggested_redirect_uri(request)
        config.save(update_fields=['oauth_redirect_uri', 'updated_at'])

    if request.method == 'POST':
        form = SlackWorkspaceSettingsForm(request.POST, instance=config)
        if form.is_valid():
            instance = form.save(commit=False)
            form.save_secrets(instance)
            instance.updated_by = request.user
            instance.save()
            invalidate_slack_workspace_config()
            messages.success(request, 'Slack integration settings saved.')
            return redirect('accounts:slack_settings')
    else:
        form = SlackWorkspaceSettingsForm(instance=config)

    return render(
        request,
        'accounts/slack_settings.html',
        {
            'form': form,
            'config': get_slack_workspace_config(),
            'suggested_redirect_uri': _suggested_redirect_uri(request),
            'has_oauth_secret': bool(config.oauth_client_secret_encrypted),
            'has_webhook_url': bool(config.webhook_url_encrypted),
            'has_bot_token': bool(config.bot_token_encrypted),
            'masked_oauth_secret': config.masked_oauth_client_secret,
            'masked_webhook_url': config.masked_webhook_url,
            'masked_bot_token': config.masked_bot_token,
            'oauth_ready': slack_oauth_configured(),
            'webhook_ready': staff_webhook_configured(),
            'chat_sync_ready': chat_sync_configured(),
            'oauth_client_id_set': bool(resolve_oauth_client_id(config)),
            'callback_path': reverse('accounts:slack_callback'),
        },
    )


@admin_required
@require_POST
def slack_test_webhook(request):
    config = get_slack_workspace_config()
    if not staff_webhook_configured():
        messages.error(request, 'Enable the staff webhook and save a webhook URL first.')
        return redirect('accounts:slack_settings')

    try:
        ok = send_slack_message('PowerHUB test — staff Slack webhook is working.')
        if not ok:
            raise ValueError('Webhook request failed — check URL and channel.')
        config.last_webhook_test_at = timezone.now()
        config.last_webhook_ok = True
        config.last_error = ''
        config.save(update_fields=['last_webhook_test_at', 'last_webhook_ok', 'last_error', 'updated_at'])
        messages.success(request, 'Test message posted to the staff Slack channel.')
    except Exception as exc:
        config.last_webhook_test_at = timezone.now()
        config.last_webhook_ok = False
        config.last_error = str(exc)[:2000]
        config.save(update_fields=['last_webhook_test_at', 'last_webhook_ok', 'last_error', 'updated_at'])
        messages.error(request, f'Webhook test failed: {exc}')
    return redirect('accounts:slack_settings')


@admin_required
@require_POST
def slack_validate_oauth(request):
    config = get_slack_workspace_config()
    try:
        if not config.oauth_enabled:
            raise ValueError('Enable personal Slack OAuth first.')
        client_id = resolve_oauth_client_id(config)
        if not client_id:
            raise ValueError('OAuth client ID is not set.')
        if not config.oauth_client_secret_encrypted:
            raise ValueError('OAuth client secret is not set.')
        redirect_uri = resolve_oauth_redirect_uri(config) or _suggested_redirect_uri(request)
        if not redirect_uri:
            raise ValueError('OAuth redirect URI is not set.')
        messages.success(
            request,
            f'OAuth config looks valid. Redirect URI: {redirect_uri}',
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('accounts:slack_settings')


@admin_required
@require_POST
def slack_test_bot(request):
    config = get_slack_workspace_config()
    channel_id = (request.POST.get('test_channel_id') or '').strip()
    if not chat_sync_configured():
        messages.error(request, 'Enable chat sync and save a bot token first.')
        return redirect('accounts:slack_settings')
    if not channel_id:
        messages.error(request, 'Enter a Slack channel ID to test.')
        return redirect('accounts:slack_settings')

    token = resolve_bot_token(config)
    try:
        post_channel_message(
            token=token,
            channel_id=channel_id,
            text='PowerHUB test — group chat sync bot is working.',
        )
        config.last_bot_test_at = timezone.now()
        config.last_bot_ok = True
        config.last_error = ''
        config.save(update_fields=['last_bot_test_at', 'last_bot_ok', 'last_error', 'updated_at'])
        messages.success(request, f'Test message posted to channel {channel_id}.')
    except SlackApiError as exc:
        config.last_bot_test_at = timezone.now()
        config.last_bot_ok = False
        config.last_error = str(exc)[:2000]
        config.save(update_fields=['last_bot_test_at', 'last_bot_ok', 'last_error', 'updated_at'])
        messages.error(request, f'Bot test failed: {exc}')
    return redirect('accounts:slack_settings')
