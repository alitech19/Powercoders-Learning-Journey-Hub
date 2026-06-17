"""Group Space and project space access control."""

from accounts.models import User
from cohorts.models import Group
from cohorts.permissions import get_teacher_group_ids, user_is_admin, user_is_teacher

from .models import Comment, GroupSpace, Post, ProjectSpace, ProjectSpaceMembership
from .space import SpaceRef


def get_accessible_groups(user):
    if user.role == User.Role.STUDENT:
        return list(Group.objects.filter(pk=user.group_id).select_related('cohort')) if user.group_id else []
    if user.role == User.Role.TEACHER:
        group_ids = get_teacher_group_ids(user)
        return list(
            Group.objects.filter(pk__in=group_ids)
            .select_related('cohort')
            .order_by('cohort__name', 'name')
        )
    if user.role == User.Role.ADMIN:
        return list(Group.objects.select_related('cohort').order_by('cohort__name', 'name'))
    return []


def get_accessible_project_spaces(user, *, include_archived=False):
    qs = ProjectSpace.objects.order_by('created_at', 'pk')
    if not include_archived:
        qs = qs.filter(is_archived=False)
    if user.role == User.Role.ADMIN:
        return list(qs)
    return list(qs.filter(memberships__user=user).distinct())


def get_listable_project_spaces(user, *, include_archived=False):
    if not user.is_authenticated or user.role != User.Role.ADMIN:
        return ProjectSpace.objects.none()
    qs = ProjectSpace.objects.order_by('-created_at', '-pk')
    if not include_archived:
        qs = qs.filter(is_archived=False)
    return qs


def get_project_membership(user, project_space):
    if not user.is_authenticated:
        return None
    return ProjectSpaceMembership.objects.filter(project_space=project_space, user=user).first()


def is_project_moderator(user, project_space):
    if user.role == User.Role.ADMIN:
        return True
    membership = get_project_membership(user, project_space)
    return membership is not None and membership.role == ProjectSpaceMembership.Role.MODERATOR


def can_access_group(user, group):
    if not user.is_authenticated or group is None:
        return False
    if user.role == User.Role.STUDENT:
        return user.group_id == group.pk
    if user.role == User.Role.TEACHER:
        return group.pk in get_teacher_group_ids(user)
    if user.role == User.Role.ADMIN:
        return True
    return False


def can_access_project_space(user, project_space):
    if not user.is_authenticated or project_space is None:
        return False
    if user.role == User.Role.ADMIN:
        return True
    return ProjectSpaceMembership.objects.filter(project_space=project_space, user=user).exists()


def can_access_space(user, space_ref: SpaceRef):
    if space_ref.kind == 'cohort_group':
        group = Group.objects.filter(pk=space_ref.pk).first()
        return can_access_group(user, group)
    project = ProjectSpace.objects.filter(pk=space_ref.pk).first()
    return can_access_project_space(user, project)


def can_access_group_space(user, group_space):
    return can_access_group(user, group_space.group)


def can_post_in_group_space(user, group_space):
    return can_access_group_space(user, group_space)


def can_post_in_project_space(user, project_space):
    if project_space.is_archived:
        return False
    if user.role == User.Role.ADMIN:
        return True
    return can_access_project_space(user, project_space)


def can_post_in_space(user, space_ref: SpaceRef):
    if space_ref.kind == 'cohort_group':
        from .services import get_group_space_for_group

        group = Group.objects.filter(pk=space_ref.pk).first()
        if group is None:
            return False
        return can_post_in_group_space(user, get_group_space_for_group(group))
    project = ProjectSpace.objects.filter(pk=space_ref.pk).first()
    if project is None:
        return False
    return can_post_in_project_space(user, project)


def can_manage_project_space(user, project_space):
    if not user.is_authenticated or project_space is None:
        return False
    return user.role == User.Role.ADMIN


def can_edit_post(user, post):
    if not user.is_authenticated or not can_access_post_space(user, post):
        return False
    return post.author_id == user.pk


def can_delete_post(user, post):
    if not user.is_authenticated or not can_access_post_space(user, post):
        return False
    if post.drive_storage_backend or post.drive_file_id:
        from google_storage.permissions import can_delete_drive_post

        return can_delete_drive_post(user, post)
    if post.author_id == user.pk:
        return True
    if post.project_space_id:
        return is_project_moderator(user, post.project_space)
    return user.role in (User.Role.TEACHER, User.Role.ADMIN)


def can_pin_post(user, post):
    if not can_access_post_space(user, post):
        return False
    if post.author_id == user.pk:
        return True
    if post.project_space_id:
        return is_project_moderator(user, post.project_space)
    return user.role in (User.Role.TEACHER, User.Role.ADMIN)


def can_comment_on_post(user, post):
    return can_access_post_space(user, post)


def can_edit_comment(user, comment):
    return user.is_authenticated and comment.author_id == user.pk


def can_delete_comment(user, comment):
    if not user.is_authenticated or not can_access_post_space(user, comment.post):
        return False
    if comment.author_id == user.pk:
        return True
    post = comment.post
    if post.project_space_id:
        return is_project_moderator(user, post.project_space)
    return user.role in (User.Role.TEACHER, User.Role.ADMIN)


def can_access_post_space(user, post):
    if post.group_space_id:
        return can_access_group_space(user, post.group_space)
    if post.project_space_id:
        return can_access_project_space(user, post.project_space)
    return False


def get_post_or_404(user, pk):
    from django.http import Http404
    from django.shortcuts import get_object_or_404

    post = get_object_or_404(
        Post.objects.select_related(
            'group_space__group__cohort',
            'project_space',
            'author',
        ).prefetch_related('comments__author'),
        pk=pk,
    )
    if not can_access_post_space(user, post):
        raise Http404
    return post


def get_comment_or_404(user, pk):
    from django.http import Http404
    from django.shortcuts import get_object_or_404

    comment = get_object_or_404(
        Comment.objects.select_related(
            'post__group_space__group',
            'post__project_space',
            'author',
        ),
        pk=pk,
    )
    if not can_access_post_space(user, comment.post):
        raise Http404
    return comment


def get_project_space_or_404(user, pk):
    from django.http import Http404
    from django.shortcuts import get_object_or_404

    project = get_object_or_404(ProjectSpace, pk=pk)
    if user.role == User.Role.ADMIN:
        return project
    if user.role == User.Role.STUDENT:
        if not ProjectSpaceMembership.objects.filter(project_space=project, user=user).exists():
            raise Http404
        return project
    if can_manage_project_space(user, project) or ProjectSpaceMembership.objects.filter(
        project_space=project,
        user=user,
    ).exists():
        return project
    raise Http404
