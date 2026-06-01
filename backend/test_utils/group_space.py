from group_space.models import Comment, Post
from group_space.services import get_group_space_for_group


def get_space_for_group(group):
    return get_group_space_for_group(group)


def make_post(
    group_space,
    author,
    *,
    body='Hello group',
    resource_label='',
    snapshot_html='',
    **kwargs,
):
    return Post.objects.create(
        group_space=group_space,
        author=author,
        body=body,
        resource_label=resource_label,
        snapshot_html=snapshot_html,
        **kwargs,
    )


def make_comment(post, author, *, body='Reply', **kwargs):
    return Comment.objects.create(post=post, author=author, body=body, **kwargs)
