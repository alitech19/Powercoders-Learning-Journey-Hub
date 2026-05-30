from django.db import migrations


def migrate_goal_comments_to_feedback(apps, schema_editor):
    GoalComment = apps.get_model('goals', 'GoalComment')
    GoalEnrollment = apps.get_model('goals', 'GoalEnrollment')
    FeedbackEntry = apps.get_model('feedback', 'FeedbackEntry')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    try:
        ct = ContentType.objects.get(app_label='goals', model='goalenrollment')
    except ContentType.DoesNotExist:
        return

    for comment in GoalComment.objects.all().iterator():
        enrollments = list(GoalEnrollment.objects.filter(goal_id=comment.goal_id))
        if len(enrollments) != 1:
            continue
        enrollment = enrollments[0]
        FeedbackEntry.objects.create(
            content_type=ct,
            object_id=enrollment.pk,
            author_id=comment.author_id,
            body=comment.body,
            created_at=comment.created_at,
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('feedback', '0001_initial'),
        ('goals', '0005_clean_milestone_titles'),
    ]

    operations = [
        migrations.RunPython(migrate_goal_comments_to_feedback, noop),
        migrations.DeleteModel(
            name='GoalComment',
        ),
    ]
