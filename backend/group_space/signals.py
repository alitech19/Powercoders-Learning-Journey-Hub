from django.db.models.signals import post_save
from django.dispatch import receiver

from cohorts.models import Group

from .models import GroupSpace, ProjectSpace


@receiver(post_save, sender=Group)
def ensure_group_space_on_group_create(sender, instance, **kwargs):
    GroupSpace.objects.get_or_create(group=instance)


@receiver(post_save, sender=ProjectSpace)
def ensure_project_resources_on_create(sender, instance, created, **kwargs):
    if not created:
        return
    from resources.services import ensure_system_project_container

    ensure_system_project_container(instance, created_by=instance.created_by)
