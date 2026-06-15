from django import template

register = template.Library()


@register.filter
def can_delete_chat_post(post, user):
    from group_space.permissions import can_delete_post

    return can_delete_post(user, post)
