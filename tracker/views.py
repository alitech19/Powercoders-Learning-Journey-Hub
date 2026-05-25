from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from cohorts.models import Cohort, Group

from .forms import (
    StudentTaskCreateForm,
    StudentTaskUpdateForm,
    SubtaskCreateForm,
    TaskCommentForm,
    TaskStatusForm,
    TaskUpdateForm,
    TeacherCohortTaskCreateForm,
    TeacherGroupTaskCreateForm,
    TeacherTaskUpdateForm,
)
from .models import Task, TaskComment, TaskUpdate
from .permissions import (
    can_comment_on_task,
    can_create_cohort_task,
    can_create_group_task,
    can_create_subtask,
    can_add_update_to_task,
    can_delete_task,
    can_edit_task_status,
    can_reply_to_comment,
    can_update_task,
    can_view_task_content,
    can_view_task_metadata,
    get_teacher_cohort_ids,
    get_teacher_group_ids,
    user_is_admin,
    user_is_student,
    user_is_teacher,
    visible_tasks_queryset,
    wrap_tasks_for_display,
)
from .services import build_comment_tree


def _get_task_for_user(user, task_id):
    task = get_object_or_404(
        Task.objects.select_related(
            'user', 'group', 'group__cohort', 'cohort', 'assignee', 'created_by', 'parent',
        ),
        pk=task_id,
    )
    if not can_view_task_metadata(user, task):
        raise Http404
    return task


@login_required
def task_list(request):
    tasks = visible_tasks_queryset(request.user)
    teacher_group_ids = get_teacher_group_ids(request.user) if user_is_teacher(request.user) else []
    teacher_groups = Group.objects.filter(pk__in=teacher_group_ids).select_related('cohort') if teacher_group_ids else []
    teacher_cohort_ids = get_teacher_cohort_ids(request.user) if user_is_teacher(request.user) else []
    teacher_cohorts = Cohort.objects.filter(pk__in=teacher_cohort_ids) if teacher_cohort_ids else []
    return render(
        request,
        'tracker/task_list.html',
        {
            'task_rows': wrap_tasks_for_display(request.user, tasks),
            'can_create_personal_task': user_is_student(request.user),
            'teacher_groups': teacher_groups,
            'teacher_cohorts': teacher_cohorts,
            'is_admin': user_is_admin(request.user),
        },
    )


@login_required
def task_create(request):
    """Student creates a personal task."""
    if not user_is_student(request.user):
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
    can_content = can_view_task_content(request.user, task)
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
        'can_edit_status': can_edit_task_status(request.user, task),
        'can_update': can_update_task(request.user, task),
        'can_delete': can_delete_task(request.user, task),
        'can_add_subtask': can_create_subtask(request.user, task),
        'can_add_update': can_add_update_to_task(request.user, task),
        'can_comment': can_comment_on_task(request.user, task),
    }
    return render(request, 'tracker/task_detail.html', context)


@login_required
def task_update(request, task_id):
    task = _get_task_for_user(request.user, task_id)
    if not can_update_task(request.user, task):
        return HttpResponseForbidden('You cannot edit this task.')

    if user_is_student(request.user):
        FormClass = StudentTaskUpdateForm
        form_kwargs = {}
    else:
        FormClass = TeacherTaskUpdateForm
        form_kwargs = {'task': task}

    if request.method == 'POST':
        form = FormClass(request.POST, instance=task, **form_kwargs)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = FormClass(instance=task, **form_kwargs)
    return render(request, 'tracker/task_form.html', {'form': form, 'title': 'Edit task'})


@login_required
def task_delete(request, task_id):
    task = _get_task_for_user(request.user, task_id)
    if not can_delete_task(request.user, task):
        return HttpResponseForbidden('You cannot delete this task.')

    can_content = can_view_task_content(request.user, task)
    display_title = task.title if can_content else 'Private task - content hidden'

    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted.')
        return redirect('tracker:task_list')

    return render(
        request,
        'tracker/task_confirm_delete.html',
        {'task': task, 'display_title': display_title},
    )


@login_required
def task_edit_status(request, task_id):
    task = _get_task_for_user(request.user, task_id)
    if not can_edit_task_status(request.user, task):
        raise Http404

    detail_task_id = task.parent_id if task.parent_id else task.pk

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
        {'form': form, 'task': task, 'detail_task_id': detail_task_id},
    )


@login_required
def subtask_create(request, task_id):
    parent = _get_task_for_user(request.user, task_id)
    if not can_create_subtask(request.user, parent):
        raise Http404

    if request.method == 'POST':
        form = SubtaskCreateForm(request.POST, parent_task=parent, user=request.user)
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
        form = SubtaskCreateForm(parent_task=parent, user=request.user)
    return render(request, 'tracker/subtask_form.html', {'form': form, 'parent': parent})


@login_required
def update_create(request, task_id):
    task = _get_task_for_user(request.user, task_id)
    if not can_add_update_to_task(request.user, task):
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
    return render(request, 'tracker/update_form.html', {'form': form, 'task': task})


@login_required
def comment_create(request, task_id):
    task = _get_task_for_user(request.user, task_id)
    if not can_comment_on_task(request.user, task):
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
    return render(request, 'tracker/comment_form.html', {'form': form, 'task': task, 'heading': 'Add comment'})


@login_required
def comment_reply_create(request, comment_id):
    parent_comment = get_object_or_404(
        TaskComment.objects.select_related(
            'task', 'task__user', 'task__group', 'task__cohort',
            'task__assignee', 'task__created_by', 'author',
        ),
        pk=comment_id,
    )
    if not can_reply_to_comment(request.user, parent_comment):
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
        {'form': form, 'task': task, 'parent_comment': parent_comment},
    )


@login_required
def group_task_create(request, group_id):
    group = get_object_or_404(Group.objects.select_related('cohort'), pk=group_id)
    if not can_create_group_task(request.user, group):
        raise Http404

    if request.method == 'POST':
        form = TeacherGroupTaskCreateForm(request.POST, group=group)
        if form.is_valid():
            task = form.save(commit=False)
            task.scope_type = Task.ScopeType.GROUP
            task.group = group
            task.cohort = None
            task.user = None
            task.created_by = request.user
            task.parent = None
            task.save()
            messages.success(request, 'Group task created.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TeacherGroupTaskCreateForm(group=group)
    return render(request, 'tracker/group_task_form.html', {'form': form, 'group': group})


@login_required
def cohort_task_create(request, cohort_id):
    cohort = get_object_or_404(Cohort, pk=cohort_id)
    if not can_create_cohort_task(request.user, cohort):
        raise Http404

    if request.method == 'POST':
        form = TeacherCohortTaskCreateForm(request.POST, cohort=cohort)
        if form.is_valid():
            task = form.save(commit=False)
            task.scope_type = Task.ScopeType.COHORT
            task.cohort = cohort
            task.group = None
            task.user = None
            task.created_by = request.user
            task.parent = None
            task.save()
            messages.success(request, 'Cohort task created.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TeacherCohortTaskCreateForm(cohort=cohort)
    return render(request, 'tracker/cohort_task_form.html', {'form': form, 'cohort': cohort})
