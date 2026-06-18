import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('group_space', '0007_slack_channel_sync'),
    ]

    operations = [
        migrations.CreateModel(
            name='SlackPendingReply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slack_channel_id', models.CharField(max_length=32)),
                ('slack_ts', models.CharField(max_length=32)),
                ('slack_thread_ts', models.CharField(max_length=32)),
                ('slack_user_id', models.CharField(max_length=64)),
                ('text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(
                        fields=('slack_channel_id', 'slack_ts'),
                        name='group_space_unique_pending_slack_ts',
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name='post',
            name='reply_to_post',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='slack_replies',
                to='group_space.post',
            ),
        ),
        migrations.AddField(
            model_name='post',
            name='slack_thread_ts',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddConstraint(
            model_name='post',
            constraint=models.UniqueConstraint(
                condition=models.Q(('slack_channel_id', ''), _negated=True)
                & models.Q(('slack_ts', ''), _negated=True),
                fields=('slack_channel_id', 'slack_ts'),
                name='group_space_post_unique_slack_message',
            ),
        ),
    ]
