from django.core.cache import cache
from django.test import TestCase

from google_storage.config import CONFIG_CACHE_KEY, get_workspace_storage_config, invalidate_workspace_storage_config
from google_storage.models import GoogleWorkspaceStorageConfig


class WorkspaceConfigTests(TestCase):
    def setUp(self):
        cache.delete(CONFIG_CACHE_KEY)

    def test_get_or_create_singleton(self):
        config = get_workspace_storage_config()
        self.assertEqual(config.id, 1)
        self.assertEqual(GoogleWorkspaceStorageConfig.objects.count(), 1)

    def test_cache_invalidated_on_save(self):
        config = get_workspace_storage_config()
        config.is_enabled = True
        config.save()
        self.assertIsNone(cache.get(CONFIG_CACHE_KEY))
        reloaded = get_workspace_storage_config()
        self.assertTrue(reloaded.is_enabled)

    def test_invalidate_clears_cache(self):
        get_workspace_storage_config()
        self.assertIsNotNone(cache.get(CONFIG_CACHE_KEY))
        invalidate_workspace_storage_config()
        self.assertIsNone(cache.get(CONFIG_CACHE_KEY))
