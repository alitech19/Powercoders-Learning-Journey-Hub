"""Slack Web API helpers for personal user notifications."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

USER_SCOPES = 'chat:write,im:write'
OAUTH_AUTHORIZE_URL = 'https://slack.com/oauth/v2/authorize'
OAUTH_ACCESS_URL = 'https://slack.com/api/oauth.v2.access'
API_BASE = 'https://slack.com/api/'


class SlackApiError(Exception):
    def __init__(self, message, *, error_code=''):
        super().__init__(message)
        self.error_code = error_code


def slack_oauth_configured() -> bool:
    return bool(settings.SLACK_CLIENT_ID and settings.SLACK_CLIENT_SECRET)


def default_redirect_uri(request) -> str:
    configured = getattr(settings, 'SLACK_REDIRECT_URI', '').strip()
    if configured:
        return configured
    site = getattr(settings, 'SITE_URL', '').rstrip('/')
    if site:
        return f'{site}/accounts/slack/callback/'
    return request.build_absolute_uri('/accounts/slack/callback/')


def build_authorize_url(*, state: str, redirect_uri: str) -> str:
    params = urllib.parse.urlencode(
        {
            'client_id': settings.SLACK_CLIENT_ID,
            'user_scope': USER_SCOPES,
            'redirect_uri': redirect_uri,
            'state': state,
        },
    )
    return f'{OAUTH_AUTHORIZE_URL}?{params}'


def exchange_oauth_code(*, code: str, redirect_uri: str) -> dict:
    payload = urllib.parse.urlencode(
        {
            'client_id': settings.SLACK_CLIENT_ID,
            'client_secret': settings.SLACK_CLIENT_SECRET,
            'code': code,
            'redirect_uri': redirect_uri,
        },
    ).encode()
    req = urllib.request.Request(
        OAUTH_ACCESS_URL,
        data=payload,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
    except urllib.error.URLError as exc:
        raise SlackApiError(f'Slack OAuth request failed: {exc}') from exc

    if not data.get('ok'):
        raise SlackApiError(
            data.get('error', 'Slack OAuth failed'),
            error_code=data.get('error', ''),
        )

    authed_user = data.get('authed_user') or {}
    access_token = authed_user.get('access_token', '').strip()
    slack_user_id = authed_user.get('id', '').strip()
    team = data.get('team') or {}
    slack_team_id = team.get('id', '').strip()

    if not access_token or not slack_user_id or not slack_team_id:
        raise SlackApiError('Slack OAuth response was missing user or team details.')

    return {
        'access_token': access_token,
        'slack_user_id': slack_user_id,
        'slack_team_id': slack_team_id,
    }


def _api_post(method: str, *, token: str, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f'{API_BASE}{method}',
        data=body,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json; charset=utf-8',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
    except urllib.error.URLError as exc:
        raise SlackApiError(f'Slack API request failed: {exc}') from exc

    if not data.get('ok'):
        raise SlackApiError(
            data.get('error', f'Slack API {method} failed'),
            error_code=data.get('error', ''),
        )
    return data


def send_user_dm(*, access_token: str, slack_user_id: str, text: str) -> str:
    opened = _api_post(
        'conversations.open',
        token=access_token,
        payload={'users': slack_user_id},
    )
    channel_id = (opened.get('channel') or {}).get('id', '').strip()
    if not channel_id:
        raise SlackApiError('Slack did not return a DM channel id.')

    posted = _api_post(
        'chat.postMessage',
        token=access_token,
        payload={'channel': channel_id, 'text': text},
    )
    return posted.get('ts', '')


def revoke_access_token(token: str) -> None:
    if not token:
        return
    payload = urllib.parse.urlencode({'token': token}).encode()
    req = urllib.request.Request(
        'https://slack.com/api/auth.revoke',
        data=payload,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
    except urllib.error.URLError as exc:
        logger.warning('Slack token revoke failed: %s', exc)
        return
    if not data.get('ok'):
        logger.warning('Slack token revoke returned error: %s', data.get('error'))
