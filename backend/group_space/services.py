import re
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ValidationError

from cohorts.models import Group

from .constants import ALLOWED_GROUP_FILE_EXTENSIONS, GROUP_FILE_MAX_BYTES
from .models import GroupSpace, Post

_URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)


def detect_urls(text):
    if not text:
        return []
    return _URL_RE.findall(text)


def post_has_link_or_file(post):
    return bool(post.file) or bool(detect_urls(post.body))


def post_is_achievement_share(post):
    """Shared journal/habit/goal/task snapshot — chat only, not a Resources item."""
    return bool(post.snapshot_html)


def post_qualifies_for_resources(post):
    if post_is_achievement_share(post):
        return False
    return post_has_link_or_file(post) and bool(post.resource_label.strip())


def primary_url_from_post(post):
    urls = detect_urls(post.body)
    return urls[0] if urls else ''


def resolve_group(groups, group_pk):
    if not groups:
        return None
    if group_pk:
        match = next((g for g in groups if str(g.pk) == str(group_pk)), None)
        return match or groups[0]
    return groups[0]


def get_group_space_for_group(group):
    space, _ = GroupSpace.objects.get_or_create(group=group)
    return space


def load_post(pk):
    return (
        Post.objects.prefetch_related('comments__author')
        .select_related('author', 'group_space__group__cohort')
        .get(pk=pk)
    )


def validate_uploaded_file(uploaded_file):
    if uploaded_file.size > GROUP_FILE_MAX_BYTES:
        raise ValidationError(
            f'File is too large. Maximum size is {GROUP_FILE_MAX_BYTES // (1024 * 1024)} MB.',
        )
    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in ALLOWED_GROUP_FILE_EXTENSIONS:
        allowed = ', '.join(sorted(ALLOWED_GROUP_FILE_EXTENSIONS))
        raise ValidationError(f'File type not allowed. Allowed: {allowed}')


def sync_group_resource_from_post(post):
    from resources.models import ResourceItem
    from resources.services import sync_from_group_post

    if not post_qualifies_for_resources(post):
        ResourceItem.objects.filter(source_post=post).delete()
        return
    sync_from_group_post(post)


def after_post_saved(post):
    sync_group_resource_from_post(post)


def feed_url_for_group(group):
    from django.urls import reverse

    return f"{reverse('group_space:feed')}?group={group.pk}"
