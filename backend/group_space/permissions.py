"""Group Space access control."""

from accounts.models import User
from cohorts.models import Group
from cohorts.permissions import get_teacher_group_ids, user_is_admin, user_is_teacher

from .models import Comment, GroupSpace, Post


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


def can_access_group_space(user, group_space):
    return can_access_group(user, group_space.group)


def can_post_in_group_space(user, group_space):
    return can_access_group_space(user, group_space)


def can_edit_post(user, post):
    return user.is_authenticated and post.author_id == user.pk and can_access_group_space(user, post.group_space)


def can_delete_post(user, post):
    if not user.is_authenticated or not can_access_group_space(user, post.group_space):
        return False
    if post.author_id == user.pk:
        return True
    return user.role in (User.Role.TEACHER, User.Role.ADMIN)


def can_pin_post(user, post):
    if not can_access_group_space(user, post.group_space):
        return False
    if post.author_id == user.pk:
        return True
    return user.role in (User.Role.TEACHER, User.Role.ADMIN)


def can_comment_on_post(user, post):
    return can_access_group_space(user, post.group_space)


def can_edit_comment(user, comment):
    return user.is_authenticated and comment.author_id == user.pk


def can_delete_comment(user, comment):
    if not user.is_authenticated or not can_access_group_space(user, comment.post.group_space):
        return False
    if comment.author_id == user.pk:
        return True
    return user.role in (User.Role.TEACHER, User.Role.ADMIN)


def get_post_or_404(user, pk):
    from django.shortcuts import get_object_or_404

    post = get_object_or_404(
        Post.objects.select_related('group_space__group__cohort', 'author')
        .prefetch_related('comments__author'),
        pk=pk,
    )
    if not can_access_group_space(user, post.group_space):
        from django.http import Http404

        raise Http404
    return post


def get_comment_or_404(user, pk):
    from django.shortcuts import get_object_or_404

    comment = get_object_or_404(
        Comment.objects.select_related('post__group_space__group', 'author'),
        pk=pk,
    )
    if not can_access_group_space(user, comment.post.group_space):
        from django.http import Http404

        raise Http404
    return comment
