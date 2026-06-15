from django.conf import settings
from django.db import models


class IntegratedModule(models.Model):
    slug = models.SlugField(unique=True)
    label = models.CharField(max_length=64)
    is_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='module_toggle_updates',
    )

    class Meta:
        verbose_name = 'integrated module'
        verbose_name_plural = 'integrated modules'
        ordering = ('slug',)

    def __str__(self):
        state = 'on' if self.is_enabled else 'off'
        return f'{self.label} ({state})'
