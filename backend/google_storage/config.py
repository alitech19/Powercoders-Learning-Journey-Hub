"""Runtime access to the Google workspace storage singleton."""

from django.core.cache import cache

from .models import GoogleWorkspaceStorageConfig

CONFIG_CACHE_KEY = 'google_storage:workspace_config'
CONFIG_CACHE_TTL = 300


def get_workspace_storage_config() -> GoogleWorkspaceStorageConfig:
    cached = cache.get(CONFIG_CACHE_KEY)
    if cached is not None:
        return cached
    config, _created = GoogleWorkspaceStorageConfig.objects.get_or_create(id=1)
    cache.set(CONFIG_CACHE_KEY, config, timeout=CONFIG_CACHE_TTL)
    return config


def invalidate_workspace_storage_config() -> None:
    cache.delete(CONFIG_CACHE_KEY)
