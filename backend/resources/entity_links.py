"""Link thematic Resources containers to workflows, tasks, and goals."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models import Q

from accounts.models import User
from config.input_limits import TITLE_MAX_LENGTH
from config.module_access import is_module_enabled
from config.text_validation import clamp_text
from group_space.permissions import get_accessible_groups

from .models import ResourceContainer
from .permissions import can_access_group


def resource_container_picker_enabled() -> bool:
    return is_module_enabled('resources')


def default_materials_title(entity_title: str) -> str:
    title = (entity_title or '').strip()
    return f'Materials: {title}' if title else 'Materials'


def list_pickable_thematic_containers(user, *, include_container=None) -> list[ResourceContainer]:
    if not user.is_authenticated:
        return []

    qs = (
        ResourceContainer.objects.filter(
            container_type=ResourceContainer.ContainerType.THEMATIC,
            is_system=False,
        )
        .select_related('group__cohort', 'created_by')
        .order_by('title', 'pk')
    )

    if user.role == User.Role.STUDENT:
        containers = list(qs.filter(created_by=user))
    else:
        group_ids = [group.pk for group in get_accessible_groups(user)]
        filters = Q(created_by=user)
        if group_ids:
            filters |= Q(group_id__in=group_ids)
        containers = list(qs.filter(filters))

    if include_container and include_container.pk not in {c.pk for c in containers}:
        if container_valid_for_staff_link(user, include_container):
            containers.append(include_container)
            containers.sort(key=lambda c: (c.title.lower(), c.pk))
    return containers


def container_valid_for_staff_link(user, container: ResourceContainer) -> bool:
    if container.is_system:
        return False
    if container.container_type != ResourceContainer.ContainerType.THEMATIC:
        return False
    if container.created_by_id == user.pk:
        return True
    if container.group_id and can_access_group(user, container.group):
        return True
    return False


def resolve_resource_container_for_entity(
    *,
    user,
    post,
    default_title: str,
    assignee_group=None,
) -> ResourceContainer | None:
    if not resource_container_picker_enabled():
        return None
    if user.role == User.Role.STUDENT:
        return None

    mode = (post.get('resource_container_mode') or 'none').strip()
    if mode in ('', 'none'):
        return None

    if mode == 'existing':
        raw_id = (post.get('resource_container_id') or '').strip()
        if not raw_id.isdigit():
            raise ValidationError('Select a materials theme or choose None.')
        container = ResourceContainer.objects.filter(pk=int(raw_id)).first()
        if container is None or not container_valid_for_staff_link(user, container):
            raise ValidationError('Selected materials theme is not available.')
        return container

    if mode == 'create':
        title = clamp_text(
            (post.get('resource_container_new_title') or '').strip() or default_title,
            TITLE_MAX_LENGTH,
        )
        if not title:
            raise ValidationError('Materials theme title is required.')
        return ResourceContainer.objects.create(
            container_type=ResourceContainer.ContainerType.THEMATIC,
            title=title,
            group=assignee_group,
            created_by=user,
            is_system=False,
        )

    raise ValidationError('Invalid materials option.')


def apply_entity_resource_container(*, entity, user, post, assignee_group=None) -> None:
    if not resource_container_picker_enabled():
        return
    if user.role == User.Role.STUDENT:
        return

    container = resolve_resource_container_for_entity(
        user=user,
        post=post,
        default_title=default_materials_title(getattr(entity, 'title', '')),
        assignee_group=assignee_group,
    )
    if entity.resource_container_id != (container.pk if container else None):
        entity.resource_container = container
        entity.save(update_fields=['resource_container', 'updated_at'])


def resource_container_picker_context(
    user,
    *,
    entity_title: str = '',
    linked_container=None,
) -> dict:
    if not resource_container_picker_enabled() or user.role == User.Role.STUDENT:
        return {'show_resource_container_picker': False}

    linked = linked_container
    initial_mode = 'none'
    if linked:
        initial_mode = 'existing'

    return {
        'show_resource_container_picker': True,
        'pickable_resource_containers': list_pickable_thematic_containers(
            user,
            include_container=linked,
        ),
        'resource_container_default_title': default_materials_title(entity_title),
        'linked_resource_container': linked,
        'resource_container_mode': initial_mode,
    }


def entity_materials_context(user, entity) -> dict:
    container = getattr(entity, 'resource_container', None)
    if container is None or not resource_container_picker_enabled():
        return {}

    from .permissions import can_view_container

    if not can_view_container(user, container):
        return {}
    return {'materials_container': container}


def can_view_container_via_entity_link(user, container: ResourceContainer) -> bool:
    from goals.models import Goal
    from goals.permissions import can_view_goal
    from tasks.models import Task
    from tasks.permissions import can_view_task_content
    from workflows.models import Workflow
    from workflows.permissions import can_view_workflow

    for workflow in Workflow.objects.filter(resource_container=container).iterator():
        if can_view_workflow(user, workflow):
            return True
    for task in Task.objects.filter(resource_container=container).iterator():
        if can_view_task_content(user, task):
            return True
    for goal in Goal.objects.filter(resource_container=container).iterator():
        if can_view_goal(user, goal):
            return True
    return False
