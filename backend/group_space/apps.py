from django.apps import AppConfig


class GroupSpaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'group_space'
    verbose_name = 'Group Space'

    def ready(self):
        import group_space.signals  # noqa: F401
