from django.contrib.auth import get_user_model

from group_space.services import detect_urls, post_qualifies_for_resources, primary_url_from_post

from .models import ResourceContainer, ResourceItem

User = get_user_model()


def ensure_system_group_container(group, *, created_by=None):
    """One system tile per cohort group — title matches group name."""
    author = created_by
    if author is None:
        author = User.objects.filter(is_superuser=True).order_by('pk').first()
    if author is None:
        author = User.objects.order_by('pk').first()
    container, created = ResourceContainer.objects.get_or_create(
        group=group,
        is_system=True,
        container_type=ResourceContainer.ContainerType.GROUP,
        defaults={
            'title': group.name,
            'created_by': author,
        },
    )
    if not created and container.title != group.name:
        container.title = group.name
        container.save(update_fields=['title', 'updated_at'])
    return container


def resource_url_for_post(post, request=None):
    urls = detect_urls(post.body)
    if urls:
        return urls[0]
    if post.file:
        url = post.file.url
        if request and url.startswith('/'):
            return request.build_absolute_uri(url)
        return url
    return ''


def sync_from_group_post(post, *, request=None):
    """Create/update/remove ResourceItem from a Group Space post (new posts only at call sites)."""
    if not post_qualifies_for_resources(post):
        ResourceItem.objects.filter(source_post=post).delete()
        return None

    group = post.group_space.group
    container = ensure_system_group_container(group, created_by=post.author)
    url = resource_url_for_post(post, request=request)
    if not url:
        ResourceItem.objects.filter(source_post=post).delete()
        return None

    item, _created = ResourceItem.objects.update_or_create(
        source_post=post,
        defaults={
            'container': container,
            'title': post.resource_label.strip(),
            'url': url,
            'created_by': post.author,
        },
    )
    return item


def next_item_sort_order(container):
    last = container.items.order_by('-sort_order').values_list('sort_order', flat=True).first()
    return (last or 0) + 1
