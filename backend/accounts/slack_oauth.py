"""Slack OAuth connect / disconnect for personal notifications."""

from __future__ import annotations

import secrets

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone

from .models import SlackIntegration
from .notifications.settings import get_notification_settings
from .slack_provider import (
    SlackApiError,
    build_authorize_url,
    default_redirect_uri,
    exchange_oauth_code,
    revoke_access_token,
    send_user_dm,
    slack_oauth_configured,
)

SESSION_STATE_KEY = 'slack_oauth_state'
SESSION_REDIRECT_KEY = 'slack_oauth_redirect_uri'


def start_connect(request):
    if not slack_oauth_configured():
        messages.error(request, 'Slack is not configured on this server yet.')
        return redirect('accounts:notification_settings')

    state = secrets.token_urlsafe(24)
    redirect_uri = default_redirect_uri(request)
    request.session[SESSION_STATE_KEY] = state
    request.session[SESSION_REDIRECT_KEY] = redirect_uri
    return redirect(build_authorize_url(state=state, redirect_uri=redirect_uri))


def finish_connect(request):
    if not slack_oauth_configured():
        messages.error(request, 'Slack is not configured on this server yet.')
        return redirect('accounts:notification_settings')

    expected_state = request.session.pop(SESSION_STATE_KEY, None)
    if not expected_state or expected_state != request.GET.get('state'):
        messages.error(request, 'Slack sign-in expired. Please try again.')
        return redirect('accounts:notification_settings')

    if request.GET.get('error'):
        messages.error(request, f"Slack sign-in cancelled: {request.GET.get('error')}")
        return redirect('accounts:notification_settings')

    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Slack did not return an authorization code.')
        return redirect('accounts:notification_settings')

    redirect_uri = request.session.pop(SESSION_REDIRECT_KEY, '') or default_redirect_uri(request)
    try:
        oauth_data = exchange_oauth_code(code=code, redirect_uri=redirect_uri)
    except SlackApiError as exc:
        messages.error(request, str(exc))
        return redirect('accounts:notification_settings')

    integration, _created = SlackIntegration.objects.update_or_create(
        user=request.user,
        defaults={
            'is_active': True,
            'slack_user_id': oauth_data['slack_user_id'],
            'slack_team_id': oauth_data['slack_team_id'],
            'disconnected_at': None,
            'last_error': '',
        },
    )
    integration.set_access_token(oauth_data['access_token'])
    integration.connected_at = timezone.now()
    integration.save()

    notif_settings = get_notification_settings(request.user)
    notif_settings.slack_enabled = True
    notif_settings.save(update_fields=['slack_enabled', 'updated_at'])

    messages.success(request, 'Slack connected successfully.')
    return redirect('accounts:notification_settings')


def disconnect(request):
    try:
        integration = request.user.slack_integration
    except SlackIntegration.DoesNotExist:
        messages.info(request, 'No Slack account is connected.')
        return redirect('accounts:notification_settings')

    revoke_access_token(integration.get_access_token())
    integration.mark_disconnected()
    messages.success(request, 'Slack disconnected.')
    return redirect('accounts:notification_settings')


def send_test_message(request):
    try:
        integration = request.user.slack_integration
    except SlackIntegration.DoesNotExist:
        messages.error(request, 'Connect Slack before sending a test message.')
        return redirect('accounts:notification_settings')

    if not integration.is_connected:
        messages.error(request, 'Connect Slack before sending a test message.')
        return redirect('accounts:notification_settings')

    try:
        send_user_dm(
            access_token=integration.get_access_token(),
            slack_user_id=integration.slack_user_id,
            text='PowerHUB test notification — your Slack connection works.',
        )
        integration.last_error = ''
        integration.save(update_fields=['last_error'])
        messages.success(request, 'Test Slack message sent.')
    except SlackApiError as exc:
        integration.last_error = str(exc)[:500]
        integration.save(update_fields=['last_error'])
        messages.error(request, f'Could not send Slack test message: {exc}')

    return redirect('accounts:notification_settings')
