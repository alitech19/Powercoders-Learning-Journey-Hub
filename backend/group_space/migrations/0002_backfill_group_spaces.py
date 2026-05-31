from django.db import migrations


def backfill_group_spaces(apps, schema_editor):
    Group = apps.get_model('cohorts', 'Group')
    GroupSpace = apps.get_model('group_space', 'GroupSpace')
    for group in Group.objects.all():
        GroupSpace.objects.get_or_create(group=group)


class Migration(migrations.Migration):

    dependencies = [
        ('group_space', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_group_spaces, migrations.RunPython.noop),
    ]
