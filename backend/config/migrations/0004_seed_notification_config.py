from django.db import migrations


def seed_notification_config(apps, schema_editor):
    NotificationConfig = apps.get_model('powerhub_config', 'NotificationConfig')
    NotificationConfig.objects.get_or_create(id=1)


class Migration(migrations.Migration):

    dependencies = [
        ('powerhub_config', '0003_notification_config'),
    ]

    operations = [
        migrations.RunPython(seed_notification_config, migrations.RunPython.noop),
    ]
