from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0002_backfill_group_containers'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourceitem',
            name='storage_backend',
            field=models.CharField(blank=True, choices=[('google_drive_shared', 'Org drive'), ('google_drive_personal', 'My Drive'), ('external_url', 'Link'), ('legacy_local', 'Legacy local file')], max_length=32),
        ),
        migrations.AddField(
            model_name='resourceitem',
            name='drive_file_id',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
