from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxLengthValidator
from django.db import models

from config.input_limits import BODY_TEXT_MAX_LENGTH


class FeedbackEntry(models.Model):
    """Staff feedback attached to any registered target (enrollment, task, etc.)."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedback_entries',
    )
    body = models.TextField(validators=[MaxLengthValidator(BODY_TEXT_MAX_LENGTH)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f'{self.author} → {self.content_type.model} #{self.object_id}'
