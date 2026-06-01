from django.db import migrations


def backfill_system_group_containers(apps, schema_editor):
    Group = apps.get_model('cohorts', 'Group')
    ResourceContainer = apps.get_model('resources', 'ResourceContainer')
    User = apps.get_model('accounts', 'User')
    author = User.objects.filter(is_superuser=True).order_by('pk').first()
    if author is None:
        author = User.objects.order_by('pk').first()
    if author is None:
        return
    for group in Group.objects.all():
        ResourceContainer.objects.get_or_create(
            group=group,
            is_system=True,
            container_type='group',
            defaults={
                'title': group.name,
                'created_by': author,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0001_initial'),
        ('cohorts', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_system_group_containers, migrations.RunPython.noop),
    ]
