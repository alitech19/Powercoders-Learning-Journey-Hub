from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_notification'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='avatar',
        ),
        migrations.AddField(
            model_name='user',
            name='avatar_content_type',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='user',
            name='avatar_data',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='avatar_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
