"""Resources access control."""

from accounts.models import User
from cohorts.permissions import get_teacher_group_ids, user_is_admin, user_is_teacher

from group_space.permissions import get_accessible_groups

from .models import ResourceContainer, ResourceItem


def can_access_group(user, group):
    if not user.is_authenticated or group is None:
        return False
    if user.role == User.Role.STUDENT:
        return user.group_id == group.pk
    if user.role == User.Role.TEACHER:
        return group.pk in get_teacher_group_ids(user)
    if user.role == User.Role.ADMIN:
        return True
    return False


def can_view_container(user, container):
    if not user.is_authenticated:
        return False
    if container.container_type == ResourceContainer.ContainerType.PERSONAL:
        return container.owner_id == user.pk
    if container.group_id and can_access_group(user, container.group):
        return True
    if container.container_type == ResourceContainer.ContainerType.PROJECT:
        from group_space.permissions import can_access_project_space

        return can_access_project_space(user, container.project_space)
    return False


def can_edit_container_items(user, container):
    if not can_view_container(user, container):
        return False
    if container.container_type == ResourceContainer.ContainerType.PERSONAL:
        return container.owner_id == user.pk
    if container.container_type == ResourceContainer.ContainerType.GROUP:
        return can_access_group(user, container.group)
    if container.container_type == ResourceContainer.ContainerType.PROJECT:
        from group_space.permissions import can_access_project_space

        if container.project_space.is_archived:
            return False
        return can_access_project_space(user, container.project_space)
    if container.container_type == ResourceContainer.ContainerType.THEMATIC:
        if container.created_by_id == user.pk:
            return True
        return user.role in (User.Role.TEACHER, User.Role.ADMIN) and can_access_group(user, container.group)
    return False


def can_create_personal_container(user):
    return user.is_authenticated


def can_create_thematic_container(user, group):
    if not can_access_group(user, group):
        return False
    return user.role in (User.Role.TEACHER, User.Role.ADMIN)


def can_delete_container(user, container):
    if container.is_system:
        return False
    if container.container_type == ResourceContainer.ContainerType.PERSONAL:
        return container.owner_id == user.pk
    if container.container_type == ResourceContainer.ContainerType.THEMATIC:
        if container.created_by_id == user.pk:
            return True
        return user.role in (User.Role.TEACHER, User.Role.ADMIN) and can_access_group(user, container.group)
    return False


def can_edit_container_metadata(user, container):
    return can_delete_container(user, container)


def get_container_or_404(user, pk):
    from django.http import Http404
    from django.shortcuts import get_object_or_404

    container = get_object_or_404(
        ResourceContainer.objects.select_related('group__cohort', 'project_space', 'owner', 'created_by'),
        pk=pk,
    )
    if not can_view_container(user, container):
        raise Http404
    return container


def get_item_or_404(user, pk):
    from django.http import Http404
    from django.shortcuts import get_object_or_404

    item = get_object_or_404(
        ResourceItem.objects.select_related('container__group', 'container__owner', 'source_post'),
        pk=pk,
    )
    if not can_view_container(user, item.container):
        raise Http404
    return item


def resolve_selected_group(user, group_pk):
    groups = get_accessible_groups(user)
    if not groups:
        return None, groups
    if group_pk:
        match = next((g for g in groups if str(g.pk) == str(group_pk)), None)
        return match or groups[0], groups
    if user.role == User.Role.STUDENT and user.group_id:
        match = next((g for g in groups if g.pk == user.group_id), None)
        if match:
            return match, groups
    return groups[0], groups
