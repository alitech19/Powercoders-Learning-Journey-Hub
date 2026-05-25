from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from cohorts.models import Group

from .forms import (
    GroupTaskCreateForm,
    StudentTaskCreateForm,
    SubtaskCreateForm,
    TaskCommentForm,
    TaskStatusForm,
    TaskUpdateForm,
)
from .models import Task, TaskComment, TaskUpdate
from .permissions import (
    get_teacher_group_ids,
    user_can_add_subtask,
    user_can_add_update,
    user_can_comment_on_task,
    user_can_create_group_task,
    user_can_edit_task_status,
    user_can_reply_to_comment,
    user_can_view_task_content,
    user_can_view_task_metadata,
    visible_tasks_queryset,
    wrap_tasks_for_display,
)
from .services import build_comment_tree


def _detail_task_id(task):
    return task.parent_id if task.parent_id else task.pk


def _get_task_for_user(user, task_id):
    task = get_object_or_404(
        Task.objects.select_related(
            'user',
            'group',
            'cohort',
            'assignee',
            'created_by',
            'parent',
        ),
        pk=task_id,
    )
    if not user_can_view_task_metadata(user, task):
        raise Http404
    return task


@login_required
def task_list(request):
    tasks = visible_tasks_queryset(request.user)
    can_create_personal = request.user.role == User.Role.STUDENT
    teacher_group_ids = get_teacher_group_ids(request.user) if request.user.role == User.Role.TEACHER else []
    teacher_groups = Group.objects.filter(pk__in=teacher_group_ids) if teacher_group_ids else []
    return render(
        request,
        'tracker/task_list.html',
        {
            'task_rows': wrap_tasks_for_display(request.user, tasks),
            'can_create_personal_task': can_create_personal,
            'teacher_groups': teacher_groups,
        },
    )


@login_required
def task_create(request):
    """Create a personal task (students only)."""
    if request.user.role != User.Role.STUDENT:
        messages.error(request, 'Only students can create personal tasks here.')
        return redirect('tracker:task_list')

    if request.method == 'POST':
        form = StudentTaskCreateForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.scope_type = Task.ScopeType.USER
            task.user = request.user
            task.parent = None
            task.created_by = request.user
            task.assignee = request.user
            task.save()
            messages.success(request, 'Personal task created.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = StudentTaskCreateForm()
    return render(request, 'tracker/task_form.html', {'form': form, 'title': 'Create personal task'})


@login_required
def task_detail(request, task_id):
    task = _get_task_for_user(request.user, task_id)
    can_content = user_can_view_task_content(request.user, task)
    subtasks = task.subtasks.select_related('assignee', 'created_by')
    updates = task.updates.select_related('author') if can_content else TaskUpdate.objects.none()
    comment_tree = build_comment_tree(task) if can_content else []

    context = {
        'task': task,
        'can_view_content': can_content,
        'display_title': task.title if can_content else 'Private task - content hidden',
        'subtask_rows': wrap_tasks_for_display(request.user, subtasks),
        'updates': updates,
        'comment_tree': comment_tree,
        'can_edit_status': user_can_edit_task_status(request.user, task),
        'can_add_subtask': user_can_add_subtask(request.user, task),
        'can_add_update': user_can_add_update(request.user, task),
        'can_comment': user_can_comment_on_task(request.user, task),
    }
    return render(request, 'tracker/task_detail.html', context)


@login_required
def task_edit_status(request, task_id):
    task = _get_task_for_user(request.user, task_id)
    if not user_can_edit_task_status(request.user, task):
        raise Http404

    detail_task_id = _detail_task_id(task)
    parent_task = None
    if task.parent_id:
        parent_task = _get_task_for_user(request.user, task.parent_id)

    if request.method == 'POST':
        form = TaskStatusForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Status updated.')
            return redirect('tracker:task_detail', task_id=detail_task_id)
    else:
        form = TaskStatusForm(instance=task)
    return render(
        request,
        'tracker/task_status_form.html',
        {
            'form': form,
            'task': task,
            'detail_task_id': detail_task_id,
            'parent_task': parent_task,
        },
    )


@login_required
def subtask_create(request, task_id):
    parent = _get_task_for_user(request.user, task_id)
    if not user_can_add_subtask(request.user, parent):
        raise Http404

    if request.method == 'POST':
        form = SubtaskCreateForm(request.POST)
        if form.is_valid():
            subtask = form.save(commit=False)
            subtask.scope_type = parent.scope_type
            subtask.user = parent.user
            subtask.group = parent.group
            subtask.cohort = parent.cohort
            subtask.parent = parent
            subtask.created_by = request.user
            subtask.visibility = parent.visibility
            if not subtask.assignee_id:
                subtask.assignee = request.user
            subtask.save()
            messages.success(request, 'Subtask created.')
            return redirect('tracker:task_detail', task_id=parent.pk)
    else:
        form = SubtaskCreateForm()
    return render(
        request,
        'tracker/subtask_form.html',
        {'form': form, 'parent': parent},
    )


@login_required
def update_create(request, task_id):
    task = _get_task_for_user(request.user, task_id)
    if not user_can_add_update(request.user, task):
        raise Http404

    if request.method == 'POST':
        form = TaskUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.task = task
            update.author = request.user
            update.save()
            messages.success(request, 'Update added.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TaskUpdateForm()
    return render(
        request,
        'tracker/update_form.html',
        {'form': form, 'task': task},
    )


@login_required
def comment_create(request, task_id):
    task = _get_task_for_user(request.user, task_id)
    if not user_can_comment_on_task(request.user, task):
        return HttpResponseForbidden('You cannot comment on this task.')

    if request.method == 'POST':
        form = TaskCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.parent = None
            comment.save()
            messages.success(request, 'Comment added.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TaskCommentForm()
    return render(
        request,
        'tracker/comment_form.html',
        {'form': form, 'task': task, 'heading': 'Add comment'},
    )


@login_required
def comment_reply_create(request, comment_id):
    parent_comment = get_object_or_404(
        TaskComment.objects.select_related(
            'task',
            'task__user',
            'task__group',
            'task__cohort',
            'task__assignee',
            'task__created_by',
            'author',
        ),
        pk=comment_id,
    )
    if not user_can_reply_to_comment(request.user, parent_comment):
        return HttpResponseForbidden('You cannot reply to this comment.')

    task = parent_comment.task
    if request.method == 'POST':
        form = TaskCommentForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.task = task
            reply.author = request.user
            reply.parent = parent_comment
            reply.save()
            messages.success(request, 'Reply added.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TaskCommentForm()
    return render(
        request,
        'tracker/comment_reply_form.html',
        {
            'form': form,
            'task': task,
            'parent_comment': parent_comment,
        },
    )


@login_required
def group_task_create(request, group_id):
    group = get_object_or_404(Group.objects.select_related('cohort'), pk=group_id)
    if not user_can_create_group_task(request.user, group):
        raise Http404

    if request.method == 'POST':
        form = GroupTaskCreateForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.scope_type = Task.ScopeType.GROUP
            task.group = group
            task.created_by = request.user
            task.visibility = Task.Visibility.PUBLIC
            task.parent = None
            if not task.assignee_id:
                task.assignee = request.user
            task.save()
            messages.success(request, 'Group task created.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = GroupTaskCreateForm()
    return render(
        request,
        'tracker/group_task_form.html',
        {'form': form, 'group': group},
    )
