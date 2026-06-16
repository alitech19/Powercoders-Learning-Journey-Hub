import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('powerhub_config', '0002_seed_integrated_modules'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationConfig',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ('deadline_reminders_enabled', models.BooleanField(default=True, help_text='Send 24h, 2h and overdue deadline reminders to students.')),
                ('reminder_offset_24h', models.BooleanField(default=True, verbose_name='Send 24h reminder')),
                ('reminder_offset_2h', models.BooleanField(default=True, verbose_name='Send 2h reminder')),
                ('reminder_offset_overdue', models.BooleanField(default=True, verbose_name='Send overdue reminder')),
                ('reflection_digest_enabled', models.BooleanField(default=True, help_text='Post missing-reflections Slack digest to staff webhook.')),
                ('reflection_reminder_day', models.CharField(choices=[('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'), ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'), ('sunday', 'Sunday')], default='monday', help_text='Day of the week for the weekly reflection digest.', max_length=10)),
                ('reflection_reminder_hour', models.PositiveSmallIntegerField(default=10, help_text='Hour (0–23, Europe/Zurich) for the weekly reflection digest.')),
                ('reflection_reminder_minute', models.PositiveSmallIntegerField(default=0, help_text='Minute (0–59) for the weekly reflection digest.')),
                ('last_reminder_run_at', models.DateTimeField(blank=True, editable=False, null=True)),
                ('last_reminder_error', models.TextField(blank=True, editable=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notification_config_updates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Notification configuration',
                'verbose_name_plural': 'Notification configuration',
            },
        ),
    ]
