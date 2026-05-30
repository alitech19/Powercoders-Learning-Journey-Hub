from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goals', '0003_goalenrollment_milestonecompletion_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='goal',
            name='goals_goal_author__4a2497_idx',
        ),
        migrations.RemoveIndex(
            model_name='goal',
            name='goals_goal_author__0b463b_idx',
        ),
        migrations.RemoveField(
            model_name='goal',
            name='achieved_at',
        ),
        migrations.RemoveField(
            model_name='goal',
            name='status',
        ),
        migrations.RemoveField(
            model_name='milestone',
            name='completed',
        ),
        migrations.AddIndex(
            model_name='goal',
            index=models.Index(fields=['visibility'], name='goals_goal_visibil_0f6646_idx'),
        ),
        migrations.AddIndex(
            model_name='goal',
            index=models.Index(fields=['created_by'], name='goals_goal_created_4cd9b2_idx'),
        ),
    ]
