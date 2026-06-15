from django.conf import settings
from django.db import models

from config.input_limits import RESOURCE_LABEL_MAX_LENGTH, TITLE_MAX_LENGTH


class ResourceContainer(models.Model):
    class ContainerType(models.TextChoices):
        PERSONAL = 'personal', 'Personal'
        GROUP = 'group', 'Group'
        THEMATIC = 'thematic', 'Thematic'

    container_type = models.CharField(max_length=20, choices=ContainerType.choices)
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    group = models.ForeignKey(
        'cohorts.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='resource_containers',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='personal_resource_containers',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_resource_containers',
    )
    is_system = models.BooleanField(
        default=False,
        help_text='Auto-created group container synced from Group chat (one per cohort group).',
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'title', 'pk']
        constraints = [
            models.UniqueConstraint(
                fields=['group'],
                condition=models.Q(is_system=True, container_type='group'),
                name='resources_one_system_container_per_group',
            ),
        ]
        indexes = [
            models.Index(fields=['container_type', 'owner']),
            models.Index(fields=['container_type', 'group']),
        ]

    def __str__(self):
        return self.title


class ResourceItem(models.Model):
    class StorageBackend(models.TextChoices):
        GOOGLE_DRIVE_SHARED = 'google_drive_shared', 'Org drive'
        GOOGLE_DRIVE_PERSONAL = 'google_drive_personal', 'My Drive'
        EXTERNAL_URL = 'external_url', 'Link'
        LEGACY_LOCAL = 'legacy_local', 'Legacy local file'

    container = models.ForeignKey(
        ResourceContainer,
        on_delete=models.CASCADE,
        related_name='items',
    )
    title = models.CharField(max_length=RESOURCE_LABEL_MAX_LENGTH)
    url = models.CharField(max_length=2048)
    storage_backend = models.CharField(
        max_length=32,
        choices=StorageBackend.choices,
        blank=True,
    )
    drive_file_id = models.CharField(max_length=128, blank=True)
    source_post = models.OneToOneField(
        'group_space.Post',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='resource_item',
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='resource_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'title', 'pk']
        indexes = [
            models.Index(fields=['container', 'sort_order']),
        ]

    def __str__(self):
        return self.title

    @property
    def from_group_chat(self):
        return self.source_post_id is not None
