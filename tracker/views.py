from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    StudentTaskCreateForm,
    SubtaskCreateForm,
    TaskCommentForm,
    TaskEditForm,
    TaskStatusForm,
    TaskUpdateForm,
    TeacherCohortTaskCreateForm,
    TeacherGroupTaskCreateForm,
    TeacherPersonalTaskCreateForm,
)
from .models import Task, TaskComment
from .permissions import (
    can_add_update_to_task,
    can_change_task_status,
    can_comment_on_task,
    can_create_cohort_task,
    can_create_group_task,
    can_create_personal_task,
    can_create_personal_task_for_user,
    can_create_subtask,
    can_delete_task,
    can_update_task,
    can_view_task,
    get_visible_tasks_for_user,
    user_is_student,
    user_is_teacher,
    wrap_tasks_for_display,
)
from .services import build_comment_tree


def _get_task_or_404(user, task_id):
    task = get_object_or_404(
        Task.objects.select_related(
            'created_by', 'assignee_user', 'assignee_group',
            'assignee_group__cohort', 'assignee_cohort', 'parent',
        ),
        pk=task_id,
    )
    if not can_view_task(user, task):
        raise Http404
    return task


@login_required
def task_list(request):
    user = request.user
    visible = get_visible_tasks_for_user(user)

    context = {
        'can_create_personal_task': can_create_personal_task(user),
        'is_teacher': user_is_teacher(user),
        'personal_tasks': wrap_tasks_for_display(user, visible.filter(assignee_type=Task.AssigneeType.USER)),
        'group_tasks': wrap_tasks_for_display(user, visible.filter(assignee_type=Task.AssigneeType.GROUP)),
        'cohort_tasks': wrap_tasks_for_display(user, visible.filter(assignee_type=Task.AssigneeType.COHORT)),
    }
    return render(request, 'tracker/task_list.html', context)


@login_required
def task_create(request):
    """Student creates personal task. Teachers redirect to their form."""
    if user_is_teacher(request.user):
        return redirect('tracker:teacher_personal_task_create')
    if not user_is_student(request.user):
        return redirect('tracker:task_list')

    if request.method == 'POST':
        form = StudentTaskCreateForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.assignee_type = Task.AssigneeType.USER
            task.assignee_user = request.user
            task.parent = None
            task.save()
            messages.success(request, 'Personal task created.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = StudentTaskCreateForm()
    return render(request, 'tracker/task_form.html', {'form': form, 'title': 'Create personal task'})


@login_required
def task_detail(request, task_id):
    task = _get_task_or_404(request.user, task_id)
    subtasks = task.subtasks.select_related('created_by', 'assignee_user')
    updates = task.updates.select_related('author')
    comment_tree = build_comment_tree(task)

    context = {
        'task': task,
        'subtask_rows': wrap_tasks_for_display(request.user, subtasks),
        'updates': updates,
        'comment_tree': comment_tree,
        'can_update': can_update_task(request.user, task),
        'can_delete': can_delete_task(request.user, task),
        'can_change_status': can_change_task_status(request.user, task),
        'can_add_subtask': can_create_subtask(request.user, task),
        'can_add_update': can_add_update_to_task(request.user, task),
        'can_comment': can_comment_on_task(request.user, task),
    }
    return render(request, 'tracker/task_detail.html', context)


@login_required
def task_update(request, task_id):
    task = _get_task_or_404(request.user, task_id)
    if not can_update_task(request.user, task):
        return HttpResponseForbidden('You cannot edit this task.')

    if request.method == 'POST':
        form = TaskEditForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TaskEditForm(instance=task)
    context = {'form': form, 'title': 'Edit task'}
    if task.parent_id:
        context['inherited_visibility'] = task.parent.get_visibility_display()
    return render(request, 'tracker/task_form.html', context)


@login_required
def task_delete(request, task_id):
    task = _get_task_or_404(request.user, task_id)
    if not can_delete_task(request.user, task):
        return HttpResponseForbidden('You cannot delete this task.')

    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted.')
        return redirect('tracker:task_list')

    return render(request, 'tracker/task_confirm_delete.html', {'task': task})


@login_required
def task_edit_status(request, task_id):
    task = _get_task_or_404(request.user, task_id)
    if not can_change_task_status(request.user, task):
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
    return render(request, 'tracker/task_status_form.html', {'form': form, 'task': task, 'detail_task_id': detail_task_id})


@login_required
def subtask_create(request, task_id):
    parent = _get_task_or_404(request.user, task_id)
    if not can_create_subtask(request.user, parent):
        raise Http404

    if request.method == 'POST':
        form = SubtaskCreateForm(request.POST)
        if form.is_valid():
            subtask = form.save(commit=False)
            subtask.parent = parent
            subtask.created_by = request.user
            subtask.assignee_type = parent.assignee_type
            subtask.assignee_user = parent.assignee_user
            subtask.assignee_group = parent.assignee_group
            subtask.assignee_cohort = parent.assignee_cohort
            subtask.visibility = parent.visibility
            subtask.save()
            messages.success(request, 'Subtask created.')
            return redirect('tracker:task_detail', task_id=parent.pk)
    else:
        form = SubtaskCreateForm()
    return render(request, 'tracker/subtask_form.html', {'form': form, 'parent': parent})


@login_required
def update_create(request, task_id):
    task = _get_task_or_404(request.user, task_id)
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
    task = _get_task_or_404(request.user, task_id)
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
        TaskComment.objects.select_related('task', 'task__created_by', 'author'),
        pk=comment_id,
    )
    task = parent_comment.task
    if not can_comment_on_task(request.user, task):
        return HttpResponseForbidden('You cannot reply to this comment.')

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
    return render(request, 'tracker/comment_reply_form.html', {'form': form, 'task': task, 'parent_comment': parent_comment})


# --- Teacher task creation ---

@login_required
def teacher_personal_task_create(request):
    if not user_is_teacher(request.user):
        return redirect('tracker:task_list')

    if request.method == 'POST':
        form = TeacherPersonalTaskCreateForm(request.POST, teacher=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            target = form.cleaned_data['assigned_user']
            if not can_create_personal_task_for_user(request.user, target):
                return HttpResponseForbidden('You cannot assign a task to this user.')
            task.created_by = request.user
            task.assignee_type = Task.AssigneeType.USER
            task.assignee_user = target
            task.parent = None
            task.save()
            messages.success(request, 'Personal task created.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TeacherPersonalTaskCreateForm(teacher=request.user)
    return render(request, 'tracker/task_form.html', {'form': form, 'title': 'Create personal task'})


@login_required
def teacher_group_task_create(request):
    if not user_is_teacher(request.user):
        raise Http404

    if request.method == 'POST':
        form = TeacherGroupTaskCreateForm(request.POST, teacher=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            group = form.cleaned_data['assigned_group']
            if not can_create_group_task(request.user, group):
                return HttpResponseForbidden('You cannot create a task for this group.')
            task.created_by = request.user
            task.assignee_type = Task.AssigneeType.GROUP
            task.assignee_group = group
            task.parent = None
            task.save()
            messages.success(request, 'Group task created.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TeacherGroupTaskCreateForm(teacher=request.user)
    return render(request, 'tracker/task_form.html', {'form': form, 'title': 'Create group task'})


@login_required
def teacher_cohort_task_create(request):
    if not user_is_teacher(request.user):
        raise Http404

    if request.method == 'POST':
        form = TeacherCohortTaskCreateForm(request.POST, teacher=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            cohort = form.cleaned_data['assigned_cohort']
            if not can_create_cohort_task(request.user, cohort):
                return HttpResponseForbidden('You cannot create a task for this cohort.')
            task.created_by = request.user
            task.assignee_type = Task.AssigneeType.COHORT
            task.assignee_cohort = cohort
            task.parent = None
            task.save()
            messages.success(request, 'Cohort task created.')
            return redirect('tracker:task_detail', task_id=task.pk)
    else:
        form = TeacherCohortTaskCreateForm(teacher=request.user)
    return render(request, 'tracker/task_form.html', {'form': form, 'title': 'Create cohort task'})
