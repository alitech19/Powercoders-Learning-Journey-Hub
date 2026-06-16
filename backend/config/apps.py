from django.apps import AppConfig


class PowerhubConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'
    label = 'powerhub_config'
    verbose_name = 'PowerHUB configuration'

    def ready(self):
        from config.admin_site import install_powerhub_admin_site

        install_powerhub_admin_site()
