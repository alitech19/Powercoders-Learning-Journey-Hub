"""In-app / email / Slack notifications for group chat posts."""

from __future__ import annotations

import re

from django.conf import settings

from accounts.models import User
from accounts.notifications.constants import EventType
from accounts.notifications.dispatcher import dispatch_event
from cohorts.models import GroupTeacher
from cohorts.permissions import get_active_students_for_group

from .models import Post, ProjectSpaceMembership
from .slack_mapping import channel_sync_active_for_post
from .space import post_space_ref

_MENTION_QUOTED_RE = re.compile(r'@"([^"]+)"')
_MENTION_TOKEN_RE = re.compile(r'@(\S+)')


def get_group_chat_participants(group):
    """Students and assigned teachers who can see this group's chat."""
    participants = list(get_active_students_for_group(group))
    teacher_ids = GroupTeacher.objects.filter(group=group).values_list('teacher_id', flat=True)
    teachers = User.objects.filter(pk__in=teacher_ids, is_active=True)
    seen = {user.pk for user in participants}
    for teacher in teachers:
        if teacher.pk not in seen:
            participants.append(teacher)
            seen.add(teacher.pk)
    return participants


def get_project_chat_participants(project_space):
    user_ids = ProjectSpaceMembership.objects.filter(
        project_space=project_space,
    ).values_list('user_id', flat=True)
    return list(User.objects.filter(pk__in=user_ids, is_active=True))


def get_space_chat_participants(post: Post) -> list:
    if post.group_space_id:
        return get_group_chat_participants(post.group_space.group)
    if post.project_space_id:
        return get_project_chat_participants(post.project_space)
    return []


def parse_mentioned_users(text, candidates):
    if not text:
        return []

    mentioned = []
    seen_ids = set()
    by_email = {user.email.lower(): user for user in candidates}
    by_name = {user.display_name.lower(): user for user in candidates}

    for match in _MENTION_QUOTED_RE.finditer(text):
        user = by_name.get(match.group(1).strip().lower())
        if user and user.pk not in seen_ids:
            mentioned.append(user)
            seen_ids.add(user.pk)

    scrubbed = _MENTION_QUOTED_RE.sub('', text)
    for match in _MENTION_TOKEN_RE.finditer(scrubbed):
        token = match.group(1).rstrip('.,!?;:')
        user = None
        if '@' in token:
            user = by_email.get(token.lower())
        else:
            user = by_name.get(token.lower())
        if user and user.pk not in seen_ids:
            mentioned.append(user)
            seen_ids.add(user.pk)
    return mentioned


def post_preview(post: Post) -> str:
    return _post_preview(post)


def _post_preview(post: Post) -> str:
    if post.body.strip():
        return post.body.strip()[:500]
    if post.resource_label.strip():
        return post.resource_label.strip()
    if post.has_snapshot:
        return 'Shared an update'
    return 'New group chat message'


def _post_url(post: Post) -> str:
    return f'{post_space_ref(post).feed_url()}#post-{post.pk}'


def notify_space_chat_post(post: Post) -> None:
    """Notify space members about a new chat post (mentions + optional all-messages)."""
    if not post.group_space_id and not post.project_space_id:
        return

    author = post.author
    participants = get_space_chat_participants(post)
    mentioned = parse_mentioned_users(post.body, participants)
    mentioned_ids = {user.pk for user in mentioned}

    space_label = post_space_ref(post).label
    author_name = author.display_name
    preview = _post_preview(post)
    relative_url = _post_url(post)
    site = getattr(settings, 'SITE_URL', '').rstrip('/')
    full_url = f'{site}{relative_url}' if relative_url else site
    skip_slack_dm = channel_sync_active_for_post(post)

    for recipient in mentioned:
        if recipient.pk == author.pk:
            continue
        _dispatch_group_chat(
            event_type=EventType.GROUP_CHAT_MENTION,
            recipient=recipient,
            dedupe_key=f'group_chat:mention:{post.pk}:{recipient.pk}',
            title=f'{author_name} mentioned you in {space_label}',
            body=preview,
            relative_url=relative_url,
            email_body=_email_body(
                recipient=recipient,
                author_name=author_name,
                group_name=space_label,
                preview=preview,
                full_url=full_url,
                intro=f'{author_name} mentioned you in {space_label}.',
            ),
            slack_text=None if skip_slack_dm else f'💬 *{author_name}* mentioned you in *{space_label}*: {preview}',
        )

    for recipient in participants:
        if recipient.pk == author.pk or recipient.pk in mentioned_ids:
            continue
        _dispatch_group_chat(
            event_type=EventType.GROUP_CHAT_ALL,
            recipient=recipient,
            dedupe_key=f'group_chat:all:{post.pk}:{recipient.pk}',
            title=f'New message in {space_label}',
            body=f'{author_name}: {preview}',
            relative_url=relative_url,
            email_body=_email_body(
                recipient=recipient,
                author_name=author_name,
                group_name=space_label,
                preview=preview,
                full_url=full_url,
                intro=f'New message in {space_label} from {author_name}.',
            ),
            slack_text=None if skip_slack_dm else f'💬 *{author_name}* in *{space_label}*: {preview}',
        )


def notify_group_chat_post(post: Post) -> None:
    """Backward-compatible alias — cohort and project spaces."""
    notify_space_chat_post(post)


def _email_body(*, recipient, author_name, group_name, preview, full_url, intro):
    return (
        f'Hi {recipient.display_name},\n\n'
        f'{intro}\n\n'
        f'---\n{preview}\n---\n\n'
        f'View it here: {full_url}\n\n'
        f'— Powercoders Team'
    )


def _dispatch_group_chat(
    *,
    event_type,
    recipient,
    dedupe_key,
    title,
    body,
    relative_url,
    email_body,
    slack_text,
):
    dispatch_event(
        event_type=event_type,
        recipients=[recipient],
        title=title,
        body=body,
        url=relative_url,
        dedupe_key=dedupe_key,
        email_subject=title,
        email_body=email_body,
        slack_text=slack_text,
    )
