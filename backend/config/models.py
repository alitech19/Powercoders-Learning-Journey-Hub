from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationConfig(models.Model):
    """Singleton — global notification/reminder settings managed through the admin UI."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)

    # Deadline reminders
    deadline_reminders_enabled = models.BooleanField(
        default=True,
        help_text='Send 24h, 2h and overdue deadline reminders to students.',
    )
    reminder_offset_24h = models.BooleanField(default=True, verbose_name='Send 24h reminder')
    reminder_offset_2h = models.BooleanField(default=True, verbose_name='Send 2h reminder')
    reminder_offset_overdue = models.BooleanField(
        default=True, verbose_name='Send overdue reminder'
    )

    # Missing-reflection weekly digest
    reflection_digest_enabled = models.BooleanField(
        default=True,
        help_text='Post missing-reflections Slack digest to staff webhook.',
    )
    reflection_reminder_day = models.CharField(
        max_length=10,
        default='monday',
        choices=[
            ('monday', 'Monday'),
            ('tuesday', 'Tuesday'),
            ('wednesday', 'Wednesday'),
            ('thursday', 'Thursday'),
            ('friday', 'Friday'),
            ('saturday', 'Saturday'),
            ('sunday', 'Sunday'),
        ],
        help_text='Day of the week for the weekly reflection digest.',
    )
    reflection_reminder_hour = models.PositiveSmallIntegerField(
        default=10,
        help_text='Hour (0–23, Europe/Zurich) for the weekly reflection digest.',
    )
    reflection_reminder_minute = models.PositiveSmallIntegerField(
        default=0,
        help_text='Minute (0–59) for the weekly reflection digest.',
    )

    last_reminder_run_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_reminder_error = models.TextField(blank=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='notification_config_updates',
    )

    class Meta:
        verbose_name = 'Notification configuration'
        verbose_name_plural = 'Notification configuration'

    def __str__(self):
        return 'Notification configuration'

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    def record_run(self, *, error: str = ''):
        self.last_reminder_run_at = timezone.now()
        self.last_reminder_error = error[:2000] if error else ''
        self.save(update_fields=['last_reminder_run_at', 'last_reminder_error'])


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
