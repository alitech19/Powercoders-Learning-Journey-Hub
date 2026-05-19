from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from cohorts.models import Group

from .forms import (
    GroupTaskCreateForm,
    SubtaskCreateForm,
    TaskCommentForm,
    TaskCreateForm,
    TaskStatusForm,
    TaskUpdateForm,
)
from .models import Task, TaskBoard, TaskComment, TaskUpdate
from .permissions import (
    user_can_add_subtask,
    user_can_add_update,
    user_can_comment_on_task,
    user_can_create_group_task,
    user_can_edit_task_status,
    user_can_view_task_content,
    user_can_view_task_metadata,
    visible_tasks_queryset,
    wrap_tasks_for_display,
    get_teacher_group_ids,
)
from .services import (
    get_or_create_cohort_board,
    get_or_create_group_board,
    get_or_create_personal_board,
)


def _get_task_for_user(user, task_id):
    task = get_object_or_404(
        Task.objects.select_related(
            'board',
            'board__user',
            'board__group',
            'board__cohort',
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
def tracker_home(request):
    return render(request, 'tracker/tracker_home.html')


@login_required
def task_list(request):
    tasks = visible_tasks_queryset(request.user)
    return render(
        request,
        'tracker/task_list.html',
        {
            'task_rows': wrap_tasks_for_display(request.user, tasks),
            'can_create_personal_task': request.user.role == User.Role.STUDENT,
        },
    )


@login_required
def task_create(request):
    """Create a personal task on the student's user-scoped board (students only)."""
    if request.user.role != User.Role.STUDENT:
        messages.error(request, 'Only students can create personal tasks here.')
        return redirect('tracker:task_list')

    board = get_or_create_personal_board(request.user)
    if request.method == 'POST':
        form = TaskCreateForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.board = board
            task.parent = None
            task.created_by = request.user
            task.assignee = request.user
            task.save()
            messages.success(request, 'Personal task created.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TaskCreateForm()
    return render(request, 'tracker/task_form.html', {'form': form, 'title': 'Create personal task'})


@login_required
def task_detail(request, task_id):
    task = _get_task_for_user(request.user, task_id)
    can_content = user_can_view_task_content(request.user, task)
    subtasks = task.subtasks.select_related('assignee', 'created_by')
    updates = task.updates.select_related('author') if can_content else TaskUpdate.objects.none()
    comments = task.comments.select_related('author') if can_content else TaskComment.objects.none()

    context = {
        'task': task,
        'can_view_content': can_content,
        'display_title': task.title if can_content else 'Private task - content hidden',
        'subtask_rows': wrap_tasks_for_display(request.user, subtasks),
        'updates': updates,
        'comments': comments,
        'can_edit_status': user_can_edit_task_status(request.user, task),
        'can_add_subtask': user_can_add_subtask(request.user, task),
        'can_add_update': user_can_add_update(request.user, task),
        'can_comment': user_can_comment_on_task(request.user, task),
        'student_user': task.board.user if task.board.scope_type == TaskBoard.ScopeType.USER else None,
    }
    return render(request, 'tracker/task_detail.html', context)


@login_required
def task_edit_status(request, task_id):
    task = _get_task_for_user(request.user, task_id)
    if not user_can_edit_task_status(request.user, task):
        raise Http404

    if request.method == 'POST':
        form = TaskStatusForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Status updated.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TaskStatusForm(instance=task)
    return render(
        request,
        'tracker/task_status_form.html',
        {'form': form, 'task': task},
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
            subtask.board = parent.board
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
        raise Http404

    if request.method == 'POST':
        form = TaskCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
            messages.success(request, 'Comment added.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TaskCommentForm()
    return render(
        request,
        'tracker/comment_form.html',
        {'form': form, 'task': task},
    )


@login_required
def group_task_create(request, group_id):
    group = get_object_or_404(Group.objects.select_related('cohort'), pk=group_id)
    if not user_can_create_group_task(request.user, group):
        raise Http404

    board = get_or_create_group_board(group, created_by=request.user)
    if request.method == 'POST':
        form = GroupTaskCreateForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.board = board
            task.created_by = request.user
            task.visibility = Task.Visibility.PUBLIC
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
