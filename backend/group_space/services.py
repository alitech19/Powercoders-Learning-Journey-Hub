import re
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ValidationError

from cohorts.models import Group

from .constants import ALLOWED_GROUP_FILE_EXTENSIONS, GROUP_FILE_MAX_BYTES
from .models import GroupSpace, Post, ProjectSpace
from .space import SpaceRef

_URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)


def detect_urls(text):
    if not text:
        return []
    return _URL_RE.findall(text)


def post_has_link_or_file(post):
    if bool(post.file) or bool(post.drive_file_id):
        return True
    if post.drive_upload_status in {
        post.DriveUploadStatus.PENDING,
        post.DriveUploadStatus.READY,
        post.DriveUploadStatus.FAILED,
    }:
        return True
    return bool(detect_urls(post.body))


def post_is_achievement_share(post):
    """Shared journal/habit/goal/task snapshot — chat only, not a Resources item."""
    return post.has_snapshot


def post_qualifies_for_resources(post):
    if post_is_achievement_share(post):
        return False
    if post.project_space_id and post.project_space.is_archived:
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


def get_space_for_ref(space_ref: SpaceRef):
    if space_ref.kind == 'cohort_group':
        group = Group.objects.filter(pk=space_ref.pk).first()
        if group is None:
            return None
        return get_group_space_for_group(group)
    return ProjectSpace.objects.filter(pk=space_ref.pk).first()


def load_post(pk):
    return (
        Post.objects.prefetch_related('comments__author')
        .select_related(
            'author',
            'group_space__group__cohort',
            'project_space',
        )
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


def sync_space_resource_from_post(post):
    from config.module_access import is_module_enabled
    from resources.models import ResourceItem
    from resources.services import sync_from_space_post

    if not is_module_enabled('resources'):
        ResourceItem.objects.filter(source_post=post).delete()
        return
    if not post_qualifies_for_resources(post):
        ResourceItem.objects.filter(source_post=post).delete()
        return
    sync_from_space_post(post)


def after_post_saved(post):
    sync_space_resource_from_post(post)
    from .slack_sync import enqueue_slack_post_lifecycle_sync

    enqueue_slack_post_lifecycle_sync(post)


def feed_url_for_group(group):
    from django.urls import reverse

    return f"{reverse('group_space:feed')}?kind=cohort_group&space={group.pk}"


def feed_url_for_space_ref(space_ref: SpaceRef) -> str:
    return space_ref.feed_url()


# Backward-compatible alias used by notifications and older imports.
sync_group_resource_from_post = sync_space_resource_from_post
