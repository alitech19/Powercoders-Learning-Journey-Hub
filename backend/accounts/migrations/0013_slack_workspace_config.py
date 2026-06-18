from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_staff_notification_prefs'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SlackWorkspaceConfig',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ('oauth_enabled', models.BooleanField(default=False, help_text='Allow users to connect personal Slack for notification DMs.')),
                ('oauth_client_id', models.CharField(blank=True, max_length=255)),
                ('oauth_client_secret_encrypted', models.TextField(blank=True)),
                ('oauth_redirect_uri', models.URLField(blank=True, max_length=512)),
                ('webhook_enabled', models.BooleanField(default=False, help_text='Post staff-channel digests (e.g. missing reflections) via incoming webhook.')),
                ('webhook_url_encrypted', models.TextField(blank=True)),
                ('last_webhook_test_at', models.DateTimeField(blank=True, null=True)),
                ('last_webhook_ok', models.BooleanField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='slack_workspace_config_updates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Slack workspace configuration',
                'verbose_name_plural': 'Slack workspace configuration',
            },
        ),
    ]
