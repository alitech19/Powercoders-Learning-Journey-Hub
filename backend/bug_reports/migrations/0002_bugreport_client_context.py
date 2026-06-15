from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('bug_reports', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bugreport',
            name='client_context',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
