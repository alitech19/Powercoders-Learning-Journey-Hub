"""Forms and helpers for per-space Slack channel mapping."""

from __future__ import annotations

from django.core.exceptions import ValidationError

from accounts.slack_workspace_config import chat_sync_configured

from .models import GroupSpace, ProjectSpace
from .slack_mapping import get_mapping_for_group_space, get_mapping_for_project_space, save_space_slack_mapping


def slack_mapping_context(*, group_space: GroupSpace | None = None, project_space: ProjectSpace | None = None) -> dict:
    if group_space is not None:
        mapping = get_mapping_for_group_space(group_space)
    elif project_space is not None:
        mapping = get_mapping_for_project_space(project_space)
    else:
        mapping = None
    return {
        'slack_mapping': mapping,
        'slack_sync_enabled': bool(mapping and mapping.is_enabled),
        'slack_channel_id': mapping.slack_channel_id if mapping else '',
        'chat_sync_configured': chat_sync_configured(),
    }


def apply_slack_mapping_from_request(
    request,
    *,
    group_space: GroupSpace | None = None,
    project_space: ProjectSpace | None = None,
) -> str | None:
    enabled = request.POST.get('slack_sync_enabled') == 'on'
    channel_id = request.POST.get('slack_channel_id', '')
    try:
        save_space_slack_mapping(
            group_space=group_space,
            project_space=project_space,
            channel_id=channel_id,
            enabled=enabled,
        )
    except ValidationError as exc:
        if hasattr(exc, 'message_dict'):
            return '; '.join(str(v) for v in exc.message_dict.values())
        return str(exc)
    return None
