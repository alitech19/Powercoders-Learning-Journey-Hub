# Manually written: remove TaskBoard, add scope fields directly to Task.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_board_to_scope(apps, schema_editor):
    """Copy scope fields from TaskBoard into Task."""
    Task = apps.get_model('tracker', 'Task')
    for task in Task.objects.select_related('board').all():
        board = task.board
        if board:
            task.scope_type = board.scope_type
            task.user = board.user
            task.group = board.group
            task.cohort = board.cohort
            task.save(update_fields=['scope_type', 'user', 'group', 'cohort'])


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0002_comment_replies_and_update_types'),
        ('cohorts', '0002_alter_cohort_options_cohort_created_at_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Add scope fields to Task (nullable initially for data migration)
        migrations.AddField(
            model_name='task',
            name='scope_type',
            field=models.CharField(
                choices=[('user', 'User'), ('group', 'Group'), ('cohort', 'Cohort')],
                default='user',
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='task',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='scoped_tasks',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='task',
            name='group',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tasks',
                to='cohorts.group',
            ),
        ),
        migrations.AddField(
            model_name='task',
            name='cohort',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tasks',
                to='cohorts.cohort',
            ),
        ),
        # 2. Migrate data from board to task scope fields
        migrations.RunPython(migrate_board_to_scope, migrations.RunPython.noop),
        # 3. Remove board FK from Task
        migrations.RemoveField(
            model_name='task',
            name='board',
        ),
        # 4. Delete TaskBoard model
        migrations.DeleteModel(
            name='TaskBoard',
        ),
    ]
