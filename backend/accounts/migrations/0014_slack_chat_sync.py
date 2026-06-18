from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_slack_workspace_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='slackworkspaceconfig',
            name='bot_token_encrypted',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='slackworkspaceconfig',
            name='chat_sync_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Mirror Group Space chat posts to mapped Slack channels (bot token).',
            ),
        ),
        migrations.AddField(
            model_name='slackworkspaceconfig',
            name='last_bot_ok',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='slackworkspaceconfig',
            name='last_bot_test_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
