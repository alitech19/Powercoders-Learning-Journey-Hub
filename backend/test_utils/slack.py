"""Helpers for Slack workspace config in tests."""

from accounts.models import SlackWorkspaceConfig
from accounts.slack_workspace_config import invalidate_slack_workspace_config


def clear_slack_workspace_config() -> None:
    config = SlackWorkspaceConfig.get()
    config.oauth_enabled = False
    config.oauth_client_id = ''
    config.oauth_client_secret_encrypted = ''
    config.oauth_redirect_uri = ''
    config.webhook_enabled = False
    config.webhook_url_encrypted = ''
    config.chat_sync_enabled = False
    config.bot_token_encrypted = ''
    config.signing_secret_encrypted = ''
    config.slack_bot_user_id = ''
    config.save()
    invalidate_slack_workspace_config()


def configure_slack_oauth(
    *,
    client_id: str = 'test-client-id',
    secret: str = 'test-client-secret',
    enabled: bool = True,
    redirect_uri: str = '',
) -> SlackWorkspaceConfig:
    config = SlackWorkspaceConfig.get()
    config.oauth_enabled = enabled
    config.oauth_client_id = client_id
    config.set_oauth_client_secret(secret)
    if redirect_uri:
        config.oauth_redirect_uri = redirect_uri
    config.save()
    invalidate_slack_workspace_config()
    return config


def configure_slack_webhook(
    *,
    url: str = 'https://hooks.slack.com/services/TEST',
    enabled: bool = True,
) -> SlackWorkspaceConfig:
    config = SlackWorkspaceConfig.get()
    config.webhook_enabled = enabled
    config.set_webhook_url(url)
    config.save()
    invalidate_slack_workspace_config()
    return config


def configure_slack_bot(
    *,
    token: str = 'xoxb-test-token',
    signing_secret: str = 'test-signing-secret',
    enabled: bool = True,
) -> SlackWorkspaceConfig:
    config = SlackWorkspaceConfig.get()
    config.chat_sync_enabled = enabled
    config.set_bot_token(token)
    if signing_secret:
        config.set_signing_secret(signing_secret)
    config.save()
    invalidate_slack_workspace_config()
    return config
