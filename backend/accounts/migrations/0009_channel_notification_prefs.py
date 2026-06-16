from django.db import migrations, models


def copy_legacy_notification_flags(apps, schema_editor):
    Settings = apps.get_model('accounts', 'UserNotificationSettings')
    for row in Settings.objects.all().iterator():
        row.email_new_workflow = row.notify_new_workflow
        row.email_new_task = row.notify_new_task
        row.email_new_goal = row.notify_new_goal
        row.email_feedback = row.notify_feedback
        row.email_deadline_reminder = row.notify_deadline_reminder
        row.email_group_chat_mentions = row.notify_group_chat_mentions
        row.email_group_chat_all_messages = row.notify_group_chat_all_messages
        row.slack_new_workflow = row.notify_new_workflow
        row.slack_new_task = row.notify_new_task
        row.slack_new_goal = row.notify_new_goal
        row.slack_feedback = row.notify_feedback
        row.slack_deadline_reminder = row.notify_deadline_reminder
        row.slack_group_chat_mentions = row.notify_group_chat_mentions
        row.slack_group_chat_all_messages = row.notify_group_chat_all_messages
        row.save(
            update_fields=[
                'email_new_workflow',
                'email_new_task',
                'email_new_goal',
                'email_feedback',
                'email_deadline_reminder',
                'email_group_chat_mentions',
                'email_group_chat_all_messages',
                'slack_new_workflow',
                'slack_new_task',
                'slack_new_goal',
                'slack_feedback',
                'slack_deadline_reminder',
                'slack_group_chat_mentions',
                'slack_group_chat_all_messages',
            ],
        )


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0008_slack_integration'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernotificationsettings',
            name='email_deadline_reminder',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='email_feedback',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='email_group_chat_all_messages',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='email_group_chat_mentions',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='email_new_goal',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='email_new_task',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='email_new_workflow',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='slack_deadline_reminder',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='slack_feedback',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='slack_group_chat_all_messages',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='slack_group_chat_mentions',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='slack_new_goal',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='slack_new_task',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usernotificationsettings',
            name='slack_new_workflow',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(copy_legacy_notification_flags, migrations.RunPython.noop),
    ]
