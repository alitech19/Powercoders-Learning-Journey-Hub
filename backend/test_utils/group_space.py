from group_space.models import Comment, Post, ProjectSpace, ProjectSpaceMembership
from group_space.services import get_group_space_for_group


def get_space_for_group(group):
    return get_group_space_for_group(group)


def make_post(
    group_space=None,
    author=None,
    *,
    project_space=None,
    body='Hello group',
    resource_label='',
    snapshot_html='',
    **kwargs,
):
    if project_space is not None:
        return Post.objects.create(
            project_space=project_space,
            author=author,
            body=body,
            resource_label=resource_label,
            snapshot_html=snapshot_html,
            **kwargs,
        )
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


def make_project_space(created_by, *, title='Project Alpha', description='', is_archived=False):
    return ProjectSpace.objects.create(
        title=title,
        description=description,
        created_by=created_by,
        is_archived=is_archived,
    )


def add_project_member(project_space, user, *, role=ProjectSpaceMembership.Role.MEMBER, added_by=None):
    return ProjectSpaceMembership.objects.create(
        project_space=project_space,
        user=user,
        role=role,
        added_by=added_by,
    )
