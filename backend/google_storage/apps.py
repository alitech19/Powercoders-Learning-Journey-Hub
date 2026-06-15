from django.apps import AppConfig


class GoogleStorageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'google_storage'
    verbose_name = 'Google Drive storage'

    def ready(self):
        import google_storage.signals  # noqa: F401
