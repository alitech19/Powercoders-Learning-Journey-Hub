from django.db.models.signals import post_save
from django.dispatch import receiver

from cohorts.models import Group

from .models import ResourceContainer
from .services import ensure_system_group_container


@receiver(post_save, sender=Group)
def ensure_group_resource_container(sender, instance, **kwargs):
    ensure_system_group_container(instance)
