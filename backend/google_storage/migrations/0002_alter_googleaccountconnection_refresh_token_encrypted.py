from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('google_storage', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='googleaccountconnection',
            name='refresh_token_encrypted',
            field=models.TextField(blank=True),
        ),
    ]
