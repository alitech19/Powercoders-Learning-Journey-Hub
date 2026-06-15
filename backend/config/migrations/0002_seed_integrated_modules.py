from django.db import migrations

from config.modules import MODULE_REGISTRY


def seed_modules(apps, schema_editor):
    IntegratedModule = apps.get_model('powerhub_config', 'IntegratedModule')
    for spec in MODULE_REGISTRY:
        IntegratedModule.objects.get_or_create(
            slug=spec.slug,
            defaults={'label': spec.label, 'is_enabled': True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ('powerhub_config', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_modules, migrations.RunPython.noop),
    ]
