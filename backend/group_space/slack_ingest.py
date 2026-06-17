"""Ingest Slack channel messages into Group Space chat."""

from __future__ import annotations

import logging

from accounts.models import SlackIntegration
from accounts.slack_workspace_config import chat_sync_configured

from .models import Post, SlackPendingReply, SpaceSlackChannel
from .permissions import can_post_in_space
from .slack_mapping import get_mapping_for_slack_channel, normalize_slack_channel_id
from .slack_sync import reconcile_pending_slack_replies
from .space import SpaceRef

logger = logging.getLogger(__name__)

_IGNORE_SUBTYPES = frozenset({
    'bot_message',
    'message_changed',
    'message_deleted',
    'channel_join',
    'channel_leave',
    'channel_topic',
    'channel_purpose',
    'channel_name',
    'channel_archive',
    'channel_unarchive',
    'ekm_access_denied',
    'group_join',
    'group_leave',
})


def _author_for_slack_user(slack_user_id: str):
    integration = (
        SlackIntegration.objects.filter(
            slack_user_id=slack_user_id,
            is_active=True,
            disconnected_at__isnull=True,
        )
        .select_related('user')
        .first()
    )
    if integration is None or not integration.user.is_active:
        return None
    return integration.user


def _space_target(mapping: SpaceSlackChannel) -> tuple[SpaceRef, object]:
    if mapping.group_space_id:
        group = mapping.group_space.group
        ref = SpaceRef(
            kind='cohort_group',
            pk=group.pk,
            label=group.name,
            subtitle=group.cohort.name,
            sort_key=(0, group.cohort.name, group.name, group.pk),
        )
        return ref, mapping.group_space
    project = mapping.project_space
    member_count = project.memberships.count()
    ref = SpaceRef(
        kind='project',
        pk=project.pk,
        label=project.title,
        subtitle=f'{member_count} member{"s" if member_count != 1 else ""}',
        sort_key=(1, project.created_at, project.pk),
        is_archived=project.is_archived,
    )
    return ref, project


def _parent_post(channel_id: str, thread_ts: str) -> Post | None:
    if not thread_ts:
        return None
    return Post.objects.filter(slack_channel_id=channel_id, slack_ts=thread_ts).first()


def should_ignore_slack_message_event(event: dict, *, bot_user_id: str = '') -> bool:
    if event.get('type') != 'message':
        return True
    subtype = (event.get('subtype') or '').strip()
    if subtype in _IGNORE_SUBTYPES:
        return True
    if event.get('bot_id') or event.get('bot_profile'):
        return True
    user_id = (event.get('user') or '').strip()
    if bot_user_id and user_id == bot_user_id:
        return True
    if not user_id:
        return True
    text = (event.get('text') or '').strip()
    if not text:
        return True
    return False


def ingest_slack_message_event(event: dict) -> Post | None:
    if not chat_sync_configured():
        return None

    channel_id = normalize_slack_channel_id(event.get('channel', ''))
    slack_ts = (event.get('ts') or '').strip()
    if not channel_id or not slack_ts:
        return None

    if Post.objects.filter(slack_channel_id=channel_id, slack_ts=slack_ts).exists():
        return None

    mapping = get_mapping_for_slack_channel(channel_id)
    if mapping is None:
        return None

    space_ref, space_obj = _space_target(mapping)
    if space_ref.is_archived:
        return None

    author = _author_for_slack_user((event.get('user') or '').strip())
    if author is None or not can_post_in_space(author, space_ref):
        logger.info('Slack ingest skipped — no mapped active user for %s', event.get('user'))
        return None

    text = (event.get('text') or '').strip()
    thread_ts = (event.get('thread_ts') or '').strip()
    is_thread_reply = bool(thread_ts and thread_ts != slack_ts)

    parent = _parent_post(channel_id, thread_ts) if is_thread_reply else None
    if is_thread_reply and parent is None:
        SlackPendingReply.objects.update_or_create(
            slack_channel_id=channel_id,
            slack_ts=slack_ts,
            defaults={
                'slack_thread_ts': thread_ts,
                'slack_user_id': event.get('user', ''),
                'text': text,
            },
        )
        return None

    post = Post(
        author=author,
        body=text,
        source_system=Post.SourceSystem.SLACK,
        slack_channel_id=channel_id,
        slack_ts=slack_ts,
        slack_thread_ts=thread_ts if is_thread_reply else '',
        reply_to_post=parent,
    )
    if mapping.group_space_id:
        post.group_space = mapping.group_space
    else:
        post.project_space = mapping.project_space
    post.save()

    reconcile_pending_slack_replies(channel_id, slack_ts)
    return post


def create_post_from_pending(pending: SlackPendingReply, parent: Post) -> Post | None:
    mapping = get_mapping_for_slack_channel(pending.slack_channel_id)
    if mapping is None:
        return None

    author = _author_for_slack_user(pending.slack_user_id)
    if author is None:
        return None

    space_ref, _space = _space_target(mapping)
    if not can_post_in_space(author, space_ref):
        return None

    post = Post(
        author=author,
        body=pending.text,
        source_system=Post.SourceSystem.SLACK,
        slack_channel_id=pending.slack_channel_id,
        slack_ts=pending.slack_ts,
        slack_thread_ts=pending.slack_thread_ts,
        reply_to_post=parent,
    )
    if mapping.group_space_id:
        post.group_space = mapping.group_space
    else:
        post.project_space = mapping.project_space
    post.save()
    return post
