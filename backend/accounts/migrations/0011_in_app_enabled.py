from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_notification_digest_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernotificationsettings',
            name='in_app_enabled',
            field=models.BooleanField(default=True),
        ),
    ]
