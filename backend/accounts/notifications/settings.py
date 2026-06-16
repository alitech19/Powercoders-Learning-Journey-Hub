from accounts.models import UserNotificationSettings


def get_notification_settings(user):
    """Return per-user notification settings, creating defaults on first access."""
    settings, _created = UserNotificationSettings.objects.get_or_create(
        user=user,
        defaults={
            'email_enabled': user.email_notifications_enabled,
            'timezone': 'Europe/Zurich',
        },
    )
    return settings


def sync_email_enabled(user, enabled):
    """Keep legacy User.email_notifications_enabled aligned with settings."""
    settings = get_notification_settings(user)
    if settings.email_enabled != enabled:
        settings.email_enabled = enabled
        settings.save(update_fields=['email_enabled', 'updated_at'])
    if user.email_notifications_enabled != enabled:
        user.email_notifications_enabled = enabled
        user.save(update_fields=['email_notifications_enabled'])
