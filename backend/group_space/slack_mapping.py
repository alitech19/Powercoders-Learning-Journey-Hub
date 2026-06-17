"""Slack channel mapping for cohort and custom group spaces."""

from __future__ import annotations

from django.core.exceptions import ValidationError

from .models import GroupSpace, ProjectSpace, SpaceSlackChannel
from .services import get_group_space_for_group


def normalize_slack_channel_id(value: str) -> str:
    return (value or '').strip().upper()


def get_mapping_for_group_space(group_space: GroupSpace) -> SpaceSlackChannel | None:
    return SpaceSlackChannel.objects.filter(group_space=group_space).first()


def get_mapping_for_project_space(project_space: ProjectSpace) -> SpaceSlackChannel | None:
    return SpaceSlackChannel.objects.filter(project_space=project_space).first()


def get_mapping_for_post(post) -> SpaceSlackChannel | None:
    if post.group_space_id:
        return get_mapping_for_group_space(post.group_space)
    if post.project_space_id:
        return get_mapping_for_project_space(post.project_space)
    return None


def mapping_for_group(group) -> SpaceSlackChannel | None:
    return get_mapping_for_group_space(get_group_space_for_group(group))


def channel_sync_active_for_post(post) -> bool:
    """True when this post's space mirrors chat to a Slack channel."""
    from accounts.slack_workspace_config import chat_sync_configured

    if not chat_sync_configured():
        return False
    mapping = get_mapping_for_post(post)
    return bool(mapping and mapping.is_enabled and mapping.slack_channel_id)


def get_mapping_for_slack_channel(channel_id: str) -> SpaceSlackChannel | None:
    channel_id = normalize_slack_channel_id(channel_id)
    if not channel_id:
        return None
    return (
        SpaceSlackChannel.objects.filter(
            slack_channel_id=channel_id,
            is_enabled=True,
        )
        .select_related('group_space__group__cohort', 'project_space')
        .first()
    )


def save_space_slack_mapping(
    *,
    group_space: GroupSpace | None = None,
    project_space: ProjectSpace | None = None,
    channel_id: str = '',
    enabled: bool = False,
) -> SpaceSlackChannel | None:
    if bool(group_space) == bool(project_space):
        raise ValidationError('Exactly one of group_space or project_space is required.')

    channel_id = normalize_slack_channel_id(channel_id)
    lookup = {'group_space': group_space, 'project_space': project_space}
    existing = SpaceSlackChannel.objects.filter(**lookup).first()

    if enabled and not channel_id:
        raise ValidationError('Slack channel ID is required when sync is enabled.')

    if not channel_id:
        if existing:
            existing.delete()
        return None

    if enabled and not channel_id.startswith('C'):
        raise ValidationError('Slack channel ID usually starts with C (e.g. C0123456789).')

    if existing:
        existing.slack_channel_id = channel_id
        existing.is_enabled = enabled
        existing.save(update_fields=['slack_channel_id', 'is_enabled', 'updated_at'])
        return existing

    return SpaceSlackChannel.objects.create(
        group_space=group_space,
        project_space=project_space,
        slack_channel_id=channel_id,
        is_enabled=enabled,
    )
