from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('group_space', '0003_chat_ordering'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='drive_storage_backend',
            field=models.CharField(blank=True, choices=[('shared_org', 'Org Shared drive'), ('personal', 'My Drive')], max_length=20),
        ),
        migrations.AddField(
            model_name='post',
            name='drive_file_id',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='post',
            name='drive_web_view_link',
            field=models.URLField(blank=True, max_length=2048),
        ),
        migrations.AddField(
            model_name='post',
            name='drive_upload_status',
            field=models.CharField(blank=True, choices=[('pending', 'Pending'), ('ready', 'Ready'), ('failed', 'Failed')], max_length=20),
        ),
        migrations.AddField(
            model_name='post',
            name='drive_upload_error',
            field=models.TextField(blank=True),
        ),
    ]
