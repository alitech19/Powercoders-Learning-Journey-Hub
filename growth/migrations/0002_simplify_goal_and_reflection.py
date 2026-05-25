"""
Simplify Goal (5 SMART fields → description + target_date + progress_percent)
and WeeklyReflection (5 Agile fields → content).

Steps:
1. Add new fields with temporary defaults.
2. Migrate existing data into the new fields.
3. Remove old fields.
"""

from django.db import migrations, models
import django.core.validators


def merge_smart_fields(apps, schema_editor):
    Goal = apps.get_model('growth', 'Goal')
    for goal in Goal.objects.all():
        parts = []
        if goal.specific:
            parts.append(f'Specific:\n{goal.specific}')
        if goal.measurable:
            parts.append(f'Measurable:\n{goal.measurable}')
        if goal.achievable:
            parts.append(f'Achievable:\n{goal.achievable}')
        if goal.relevant:
            parts.append(f'Relevant:\n{goal.relevant}')
        goal.description = '\n\n'.join(parts) if parts else ''
        goal.target_date = goal.time_bound
        goal.save(update_fields=['description', 'target_date'])


def merge_agile_fields(apps, schema_editor):
    WeeklyReflection = apps.get_model('growth', 'WeeklyReflection')
    for ref in WeeklyReflection.objects.all():
        parts = []
        if ref.more_of:
            parts.append(f'More of:\n{ref.more_of}')
        if ref.less_of:
            parts.append(f'Less of:\n{ref.less_of}')
        if ref.start_doing:
            parts.append(f'Start doing:\n{ref.start_doing}')
        if ref.stop_doing:
            parts.append(f'Stop doing:\n{ref.stop_doing}')
        if ref.continue_doing:
            parts.append(f'Continue doing:\n{ref.continue_doing}')
        ref.content = '\n\n'.join(parts) if parts else ''
        ref.save(update_fields=['content'])


class Migration(migrations.Migration):

    dependencies = [
        ('growth', '0001_initial'),
    ]

    operations = [
        # --- Step 1: add new fields ---
        migrations.AddField(
            model_name='goal',
            name='description',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='goal',
            name='target_date',
            field=models.DateField(default='2026-01-01'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='goal',
            name='progress_percent',
            field=models.PositiveSmallIntegerField(
                default=0,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100),
                ],
            ),
        ),
        migrations.AddField(
            model_name='weeklyreflection',
            name='content',
            field=models.TextField(default=''),
            preserve_default=False,
        ),

        # --- Step 2: migrate data ---
        migrations.RunPython(merge_smart_fields, migrations.RunPython.noop),
        migrations.RunPython(merge_agile_fields, migrations.RunPython.noop),

        # --- Step 3: remove old fields ---
        migrations.RemoveField(model_name='goal', name='specific'),
        migrations.RemoveField(model_name='goal', name='measurable'),
        migrations.RemoveField(model_name='goal', name='achievable'),
        migrations.RemoveField(model_name='goal', name='relevant'),
        migrations.RemoveField(model_name='goal', name='time_bound'),
        migrations.RemoveField(model_name='weeklyreflection', name='more_of'),
        migrations.RemoveField(model_name='weeklyreflection', name='less_of'),
        migrations.RemoveField(model_name='weeklyreflection', name='start_doing'),
        migrations.RemoveField(model_name='weeklyreflection', name='stop_doing'),
        migrations.RemoveField(model_name='weeklyreflection', name='continue_doing'),
    ]
