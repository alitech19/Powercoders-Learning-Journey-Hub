from resources.models import ResourceContainer, ResourceItem
from resources.services import ensure_system_group_container


def make_personal_container(owner, *, title='My links', **kwargs):
    return ResourceContainer.objects.create(
        container_type=ResourceContainer.ContainerType.PERSONAL,
        title=title,
        owner=owner,
        created_by=owner,
        **kwargs,
    )


def make_thematic_container(group, created_by, *, title='Theme', **kwargs):
    return ResourceContainer.objects.create(
        container_type=ResourceContainer.ContainerType.THEMATIC,
        title=title,
        group=group,
        created_by=created_by,
        **kwargs,
    )


def system_group_container(group, created_by=None):
    return ensure_system_group_container(group, created_by=created_by)


def make_item(container, created_by, *, title='Link', url='https://example.com', **kwargs):
    return ResourceItem.objects.create(
        container=container,
        title=title,
        url=url,
        created_by=created_by,
        **kwargs,
    )
