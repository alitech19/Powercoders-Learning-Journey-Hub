from django.apps import AppConfig


class PowerhubConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'
    label = 'powerhub_config'
    verbose_name = 'PowerHUB configuration'
