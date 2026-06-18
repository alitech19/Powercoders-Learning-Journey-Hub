"""Runtime access to Slack workspace singleton (OAuth + staff webhook)."""

from __future__ import annotations

from django.core.cache import cache

from .models import SlackWorkspaceConfig

CONFIG_CACHE_KEY = 'accounts:slack_workspace_config'
CONFIG_CACHE_TTL = 300


def get_slack_workspace_config() -> SlackWorkspaceConfig:
    cached = cache.get(CONFIG_CACHE_KEY)
    if cached is not None:
        return cached
    config = SlackWorkspaceConfig.get()
    cache.set(CONFIG_CACHE_KEY, config, timeout=CONFIG_CACHE_TTL)
    return config


def invalidate_slack_workspace_config() -> None:
    cache.delete(CONFIG_CACHE_KEY)


def resolve_oauth_client_id(config: SlackWorkspaceConfig | None = None) -> str:
    config = config or get_slack_workspace_config()
    return config.oauth_client_id.strip()


def resolve_oauth_client_secret(config: SlackWorkspaceConfig | None = None) -> str:
    config = config or get_slack_workspace_config()
    return config.get_oauth_client_secret()


def resolve_oauth_redirect_uri(config: SlackWorkspaceConfig | None = None) -> str:
    config = config or get_slack_workspace_config()
    return config.oauth_redirect_uri.strip()


def slack_oauth_configured() -> bool:
    config = get_slack_workspace_config()
    if not config.oauth_enabled:
        return False
    return bool(resolve_oauth_client_id(config) and resolve_oauth_client_secret(config))


def staff_webhook_configured() -> bool:
    config = get_slack_workspace_config()
    if not config.webhook_enabled:
        return False
    return bool(resolve_webhook_url(config))


def resolve_webhook_url(config: SlackWorkspaceConfig | None = None) -> str:
    config = config or get_slack_workspace_config()
    return config.get_webhook_url()


def resolve_bot_token(config: SlackWorkspaceConfig | None = None) -> str:
    config = config or get_slack_workspace_config()
    return config.get_bot_token()


def chat_sync_configured() -> bool:
    config = get_slack_workspace_config()
    if not config.chat_sync_enabled:
        return False
    return bool(resolve_bot_token(config))


def slack_events_configured() -> bool:
    config = get_slack_workspace_config()
    if not config.chat_sync_enabled:
        return False
    return bool(resolve_signing_secret(config))


def resolve_signing_secret(config: SlackWorkspaceConfig | None = None) -> str:
    config = config or get_slack_workspace_config()
    return config.get_signing_secret()
