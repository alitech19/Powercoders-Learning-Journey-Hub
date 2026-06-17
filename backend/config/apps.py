from django.apps import AppConfig


class PowerhubConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'
    label = 'powerhub_config'
    verbose_name = 'PowerHUB configuration'

    def ready(self):
        from django.db.models.signals import post_migrate

        from config.admin_site import install_powerhub_admin_site

        install_powerhub_admin_site()

        def sync_notification_schedules_after_migrate(sender, **kwargs):
            if sender.label != 'powerhub_config':
                return
            try:
                from config.models import NotificationConfig
                from config.notification_schedules import sync_notification_schedules

                NotificationConfig.get()
                sync_notification_schedules()
            except Exception:
                pass

        post_migrate.connect(
            sync_notification_schedules_after_migrate,
            dispatch_uid='powerhub_config.sync_notification_schedules',
        )
