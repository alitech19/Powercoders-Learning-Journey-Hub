from django import template

register = template.Library()


@register.filter
def can_retry_drive_upload(post, user):
    from google_storage.permissions import can_retry_drive_upload as _can_retry

    return _can_retry(user, post)


@register.filter
def can_delete_chat_post(post, user):
    from group_space.permissions import can_delete_post

    return can_delete_post(user, post)
