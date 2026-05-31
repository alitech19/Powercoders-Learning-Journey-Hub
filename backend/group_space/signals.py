from django.db.models.signals import post_save
from django.dispatch import receiver

from cohorts.models import Group

from .models import GroupSpace


@receiver(post_save, sender=Group)
def ensure_group_space_on_group_create(sender, instance, **kwargs):
    GroupSpace.objects.get_or_create(group=instance)
