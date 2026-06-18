from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('group_space', '0006_projectspacemembership_alter_post_group_space_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpaceSlackChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slack_channel_id', models.CharField(help_text='Slack channel ID (e.g. C0123456789). The bot must be invited to the channel.', max_length=32)),
                ('is_enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group_space', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='slack_channel', to='group_space.groupspace')),
                ('project_space', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='slack_channel', to='group_space.projectspace')),
            ],
        ),
        migrations.AddField(
            model_name='post',
            name='slack_channel_id',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name='post',
            name='slack_ts',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name='post',
            name='source_system',
            field=models.CharField(choices=[('powerhub', 'PowerHUB'), ('slack', 'Slack')], default='powerhub', max_length=20),
        ),
        migrations.AddIndex(
            model_name='post',
            index=models.Index(fields=['slack_channel_id', 'slack_ts'], name='group_space_slack__a1b2c3_idx'),
        ),
        migrations.AddConstraint(
            model_name='spaceslackchannel',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(('group_space__isnull', False), ('project_space__isnull', True)),
                    models.Q(('group_space__isnull', True), ('project_space__isnull', False)),
                    _connector='OR',
                ),
                name='group_space_slack_exactly_one_parent',
            ),
        ),
    ]
