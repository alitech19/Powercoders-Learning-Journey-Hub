from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_slack_chat_sync'),
    ]

    operations = [
        migrations.AddField(
            model_name='slackworkspaceconfig',
            name='signing_secret_encrypted',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='slackworkspaceconfig',
            name='slack_bot_user_id',
            field=models.CharField(
                blank=True,
                help_text='Cached from auth.test — used to ignore the bot’s own channel messages.',
                max_length=32,
            ),
        ),
    ]
