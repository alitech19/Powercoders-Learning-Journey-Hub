"""One-way Group Space chat → Slack channel sync."""

from __future__ import annotations

import logging

from django.conf import settings

from accounts.slack_provider import SlackApiError, post_channel_message
from accounts.slack_workspace_config import chat_sync_configured, resolve_bot_token

from .models import Post
from .notifications import post_preview
from .slack_mapping import get_mapping_for_post
from .space import post_space_ref

logger = logging.getLogger(__name__)


def space_label_for_post(post: Post) -> str:
    return post_space_ref(post).label


def post_permalink(post: Post) -> str:
    site = getattr(settings, 'SITE_URL', '').rstrip('/')
    relative = post_space_ref(post).feed_url()
    if post.pk:
        relative = f'{relative}#post-{post.pk}'
    return f'{site}{relative}' if site else relative


def format_slack_channel_message(post: Post) -> str:
    author = post.author.display_name
    space = space_label_for_post(post)
    preview = post_preview(post)
    url = post_permalink(post)
    lines = [f'*{author}* in *{space}*: {preview}']
    if url:
        lines.append(f'<{url}|Open in PowerHUB>')
    return '\n'.join(lines)


def should_sync_post_to_slack(post: Post) -> bool:
    if post.source_system != Post.SourceSystem.POWERHUB:
        return False
    if post.slack_ts:
        return False
    if post.project_space_id and post.project_space.is_archived:
        return False
    mapping = get_mapping_for_post(post)
    return bool(mapping and mapping.is_enabled and mapping.slack_channel_id and chat_sync_configured())


def enqueue_slack_channel_sync(post: Post) -> None:
    if not should_sync_post_to_slack(post):
        return
    from .tasks import sync_post_to_slack_channel_task

    sync_post_to_slack_channel_task.delay(post.pk)


def deliver_post_to_slack_channel(post_id: int) -> bool:
    post = (
        Post.objects.select_related(
            'author',
            'group_space__group__cohort',
            'project_space',
        )
        .filter(pk=post_id)
        .first()
    )
    if post is None or not should_sync_post_to_slack(post):
        return False

    mapping = get_mapping_for_post(post)
    if mapping is None:
        return False

    token = resolve_bot_token()
    if not token:
        return False

    try:
        ts = post_channel_message(
            token=token,
            channel_id=mapping.slack_channel_id,
            text=format_slack_channel_message(post),
        )
    except SlackApiError as exc:
        logger.warning('Slack channel sync failed for post %s: %s', post_id, exc)
        return False

    Post.objects.filter(pk=post.pk).update(
        slack_channel_id=mapping.slack_channel_id,
        slack_ts=ts,
    )
    reconcile_pending_slack_replies(mapping.slack_channel_id, ts)
    return True


def reconcile_pending_slack_replies(channel_id: str, thread_ts: str) -> int:
    """Attach pending Slack thread replies once the parent message has a slack_ts."""
    from .models import SlackPendingReply
    from .slack_ingest import create_post_from_pending

    if not channel_id or not thread_ts:
        return 0

    parent = Post.objects.filter(slack_channel_id=channel_id, slack_ts=thread_ts).first()
    if parent is None:
        return 0

    created = 0
    pending_qs = SlackPendingReply.objects.filter(
        slack_channel_id=channel_id,
        slack_thread_ts=thread_ts,
    )
    for pending in list(pending_qs):
        if Post.objects.filter(slack_channel_id=channel_id, slack_ts=pending.slack_ts).exists():
            pending.delete()
            continue
        if create_post_from_pending(pending, parent):
            pending.delete()
            created += 1
    return created
