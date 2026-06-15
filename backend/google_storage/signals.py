from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .config import invalidate_workspace_storage_config
from .models import GoogleWorkspaceStorageConfig


@receiver(post_save, sender=GoogleWorkspaceStorageConfig)
@receiver(post_delete, sender=GoogleWorkspaceStorageConfig)
def _clear_config_cache(**kwargs):
    invalidate_workspace_storage_config()
