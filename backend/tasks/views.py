from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django import forms as django_forms
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.notifications.staff_events import (
    maybe_notify_workflow_completed,
    notify_student_task_completed,
)
from cohorts.permissions import (
    get_teacher_accessible_students,
    user_is_admin,
    user_is_staff,
    user_is_student,
)

from feedback.services import build_section_context

from config.entity_publish import (
    apply_publish_schedule_from_post,
    cancel_scheduled_publish,
    scheduled_publish_detail_context,
    scheduled_publish_form_defaults,
    scheduled_publish_picker_context,
)
from resources.entity_links import apply_entity_resource_container, entity_materials_context, resource_container_picker_context

from .forms import SubtaskForm, TaskCommentForm, TaskForm, TaskUpdateForm
from .models import Subtask, SubtaskEnrollment, Task, TaskComment, TaskEnrollment, TaskUpdate
from .permissions import (
    can_add_enrollment,
    can_add_participant_subtask,
    can_add_template_subtask,
    can_add_update,
    can_change_status,
    can_change_subtask_status,
    can_delete_subtask,
    can_edit_subtask,
    can_comment,
    can_create_tasks,
    can_delete_task,
    can_edit_task,
    can_edit_task_fields,
    can_manage_task,
    can_view_task,
    can_view_task_content,
    can_view_task_metadata,
    get_enrollment_for_user,
    get_visible_enrollments_for_user,
    get_visible_tasks_for_user,
    is_personal_task,
    is_staff_assigned,
    task_allows_comments,
    task_allows_subtasks,
    task_allows_updates,
)
from .services import (
    add_task_enrollments,
    build_comment_tree,
    create_group_task,
    create_student_task,
    create_tasks_bulk,
    ensure_enrollment_for_subtasks,
    get_assignment_form_context,
    set_subtask_status,
    sync_subtask_enrollments,
    sync_subtasks,
)


def _task_queryset():
    return (
        Task.objects.select_related(
            'author',
            'created_by',
            'assignee_user',
            'assignee_group',
            'assignee_group__cohort',
            'assignee_cohort',
            'resource_container',
        )
        .prefetch_related(
            'subtasks',
            Prefetch(
                'enrollments',
                queryset=TaskEnrollment.objects.select_related('student', 'student__group'),
            ),
        )
    )


def _get_task_or_404(user, pk):
    task = get_object_or_404(_task_queryset(), pk=pk)
    if not can_view_task(user, task):
        raise Http404
    return task


def _get_enrollment_or_404(user, enrollment_pk):
    enrollment = get_object_or_404(
        TaskEnrollment.objects.select_related('task', 'student', 'student__group'),
        pk=enrollment_pk,
    )
    if not can_view_task(user, enrollment.task):
        raise Http404
    return enrollment


def _effective_status(task, enrollment):
    if task.is_group_shared:
        return task.status
    return enrollment.status if enrollment else task.status


def _task_status_context(user, task, enrollment):
    return {
        'task': task,
        'enrollment': enrollment,
        'can_edit_status': can_change_status(user, task, enrollment),
        'status_choices': Task.Status.choices,
        'display_status': _effective_status(task, enrollment),
    }


def _subtask_status_map(enrollment):
    return {
        row.subtask_id: row
        for row in enrollment.subtask_enrollments.all()
    }


def _subtask_row(user, enrollment, subtask, status_map, *, readonly=False):
    row = status_map.get(subtask.pk)
    if readonly:
        return {
            'subtask': subtask,
            'display_status': row.status if row else Task.Status.TODO,
            'can_change_status': False,
            'can_edit': False,
            'can_delete': False,
        }
    return {
        'subtask': subtask,
        'display_status': row.status if row else Task.Status.TODO,
        'can_change_status': can_change_subtask_status(user, enrollment, subtask),
        'can_edit': can_edit_subtask(user, subtask),
        'can_delete': can_delete_subtask(user, subtask),
    }


def _subtask_ctx_for_staff_personal(user, enrollment):
    sync_subtask_enrollments(enrollment)
    enrollment = TaskEnrollment.objects.prefetch_related(
        'subtask_enrollments',
        'task__subtasks',
    ).get(pk=enrollment.pk)
    status_map = _subtask_status_map(enrollment)
    items = [
        _subtask_row(user, enrollment, subtask, status_map, readonly=True)
        for subtask in enrollment.subtasks_for_student().order_by('order', 'pk')
    ]
    return {
        'template_subtasks': items,
        'participant_subtasks': [],
        'subtask_done': sum(
            1 for item in items if item['display_status'] == Task.Status.DONE
        ),
        'subtask_total': len(items),
        'can_add_template_subtask': False,
        'can_add_participant_subtask': False,
        'show_staff_subtasks': True,
    }


def _subtask_ctx(user, enrollment):
    sync_subtask_enrollments(enrollment)
    enrollment = TaskEnrollment.objects.prefetch_related(
        'subtask_enrollments',
        'task__subtasks',
    ).get(pk=enrollment.pk)
    task = enrollment.task
    status_map = _subtask_status_map(enrollment)
    template_subtasks = [
        _subtask_row(user, enrollment, st, status_map)
        for st in task.subtasks.filter(added_by__isnull=True).order_by('order', 'pk')
    ]
    participant_subtasks = [
        _subtask_row(user, enrollment, st, status_map)
        for st in task.subtasks.filter(added_by=enrollment.student).order_by('order', 'pk')
    ]
    all_items = template_subtasks + participant_subtasks
    return {
        'template_subtasks': template_subtasks,
        'participant_subtasks': participant_subtasks,
        'subtask_done': sum(
            1 for item in all_items if item['display_status'] == Task.Status.DONE
        ),
        'subtask_total': len(all_items),
        'can_change_subtask_status': can_change_subtask_status(user, enrollment),
        'can_add_participant_subtask': can_add_participant_subtask(user, task, enrollment),
        'can_add_template_subtask': can_add_template_subtask(user, task),
        'status_choices': Task.Status.choices,
    }


def _apply_feedback_context(ctx, *, target, viewer):
    feedback_ctx = build_section_context(target=target, viewer=viewer)
    if feedback_ctx:
        ctx.update(feedback_ctx)
        ctx['show_feedback'] = True
    else:
        ctx['show_feedback'] = False
    return ctx


def _visibility_form_mode(user, *, task=None, creating=False):
    if creating:
        return 'staff' if user_is_staff(user) else 'student'
    if task and user_is_staff(user) and is_staff_assigned(task):
        return 'staff'
    return 'student'


def _build_list_rows(tasks, *, user, filtered_student=None):
    rows = []
    for task in tasks:
        enrollment = None
        if task.is_group_shared:
            pass
        elif user_is_student(user):
            enrollment = get_enrollment_for_user(user, task)
        elif filtered_student:
            enrollment = task.enrollments.filter(student=filtered_student).first()
        rows.append({
            'task': task,
            'enrollment': enrollment,
            'kind': task.list_kind,
            'can_view_content': can_view_task_content(user, task),
            'can_view_metadata': can_view_task_metadata(user, task),
            'can_edit_status': can_change_status(user, task, enrollment),
            'display_status': _effective_status(task, enrollment),
        })
    return rows


TASK_LIST_SECTIONS = {
    'student': [
        {
            'kind': Task.ListKind.INDIVIDUAL,
            'label': 'Individual',
            'description': 'Your personal tasks and assignments with individual progress.',
            'accent': 'border-l-blue-500',
            'badge': 'bg-blue-50 text-blue-700',
        },
        {
            'kind': Task.ListKind.GROUP,
            'label': 'Group',
            'description': 'Shared tasks for your study group — one status for everyone.',
            'accent': 'border-l-orange-500',
            'badge': 'bg-orange-50 text-orange-700',
        },
        {
            'kind': Task.ListKind.COHORT,
            'label': 'Cohort',
            'description': 'Tasks assigned to your cohort — track your own progress.',
            'accent': 'border-l-purple-500',
            'badge': 'bg-purple-50 text-purple-700',
        },
    ],
    'staff': [
        {
            'kind': Task.ListKind.INDIVIDUAL,
            'label': 'Individual',
            'description': 'Personal student tasks and per-student assignments from a group pick.',
            'accent': 'border-l-blue-500',
            'badge': 'bg-blue-50 text-blue-700',
        },
        {
            'kind': Task.ListKind.GROUP,
            'label': 'Group',
            'description': 'Shared group tasks — single progress for the whole group.',
            'accent': 'border-l-orange-500',
            'badge': 'bg-orange-50 text-orange-700',
        },
        {
            'kind': Task.ListKind.COHORT,
            'label': 'Cohort',
            'description': 'One task per cohort — each enrolled student progresses individually.',
            'accent': 'border-l-purple-500',
            'badge': 'bg-purple-50 text-purple-700',
        },
    ],
}


def _build_task_sections(rows, *, view_as):
    section_meta = TASK_LIST_SECTIONS['student' if view_as == 'student' else 'staff']
    by_kind = {meta['kind']: [] for meta in section_meta}
    for row in rows:
        by_kind[row['kind']].append(row)
    return [{**meta, 'rows': by_kind[meta['kind']]} for meta in section_meta]


def _sort_tasks(qs, sort_by):
    if sort_by == 'due':
        return qs.order_by('due_date', '-updated_at')
    if sort_by == 'priority':
        priority_order = {
            Task.Priority.HIGH: 0,
            Task.Priority.NORMAL: 1,
            Task.Priority.LOW: 2,
        }
        return sorted(qs, key=lambda t: (priority_order.get(t.priority, 9), -t.updated_at.timestamp()))
    return qs.order_by('-updated_at', '-created_at')


@login_required
def task_list(request):
    user = request.user
    status_filter = request.GET.get('status', 'active')
    if status_filter == 'done':
        status_filter = 'finished'
    elif status_filter in ('', 'todo', 'doing', 'blocked'):
        status_filter = 'active'
    sort_by = request.GET.get('sort', 'due')
    kind_filter = request.GET.get('kind', '')
    qs = get_visible_tasks_for_user(user)

    if kind_filter in Task.ListKind.values:
        if kind_filter == Task.ListKind.GROUP:
            qs = qs.filter(assignee_type=Task.AssigneeType.GROUP)
        elif kind_filter == Task.ListKind.COHORT:
            qs = qs.filter(assignee_cohort__isnull=False)
        else:
            qs = qs.filter(
                assignee_type=Task.AssigneeType.USER,
                assignee_cohort__isnull=True,
            )

    if status_filter == 'finished':
        if user_is_student(user):
            qs = qs.filter(models_q_finished_filter(user))
        else:
            qs = qs.filter(models_q_finished_filter_staff())
    else:
        if user_is_student(user):
            qs = qs.filter(models_q_active_filter(user))
        else:
            qs = qs.filter(models_q_active_filter_staff())

    if user_is_student(user):
        visible = get_visible_tasks_for_user(user)
        enrollments = TaskEnrollment.objects.filter(task__in=visible, student=user)
        group_qs = visible.filter(
            assignee_type=Task.AssigneeType.GROUP,
            assignee_group_id=user.group_id,
            visibility=Task.Visibility.SHARED,
        )
        context = {
            'status_filter': status_filter,
            'sort_by': sort_by,
            'kind_filter': kind_filter,
            'total': enrollments.count() + group_qs.count(),
            'doing': (
                enrollments.filter(status=Task.Status.DOING).count()
                + group_qs.filter(status=Task.Status.DOING).count()
            ),
            'done': (
                enrollments.filter(status=Task.Status.DONE).count()
                + group_qs.filter(status=Task.Status.DONE).count()
            ),
            'view_as': 'student',
            'status_choices': Task.Status.choices,
            'can_create': can_create_tasks(user),
            'can_create_personal_task': can_create_tasks(user),
        }
        filtered_student = None
    else:
        student_pk = request.GET.get('student', '')
        if student_pk:
            qs = qs.filter(
                models_q_student_filter(student_pk),
            )
        if user_is_admin(user):
            students = User.objects.filter(role=User.Role.STUDENT, is_active=True).order_by('display_name')
        else:
            students = get_teacher_accessible_students(user)
        filtered_student = students.filter(pk=student_pk).first() if student_pk else None
        context = {
            'students': students,
            'student_filter': student_pk,
            'filtered_student': filtered_student,
            'status_filter': status_filter,
            'sort_by': sort_by,
            'kind_filter': kind_filter,
            'status_choices': Task.Status.choices,
            'view_as': 'admin' if user_is_admin(user) else 'teacher',
            'can_create': can_create_tasks(user),
            'can_create_personal_task': False,
        }

    qs = qs.distinct()
    if sort_by == 'priority':
        tasks = _sort_tasks(list(qs), sort_by)
    else:
        tasks = list(_sort_tasks(qs, sort_by))

    all_rows = _build_list_rows(tasks, user=user, filtered_student=filtered_student)
    view_as = context['view_as']

    if kind_filter:
        paginator = Paginator(all_rows, 15)
        page_obj = paginator.get_page(request.GET.get('page'))
        context['task_rows'] = page_obj
        context['page_obj'] = page_obj
        context['task_sections'] = []
        context['has_any_tasks'] = bool(all_rows)
    else:
        context['task_sections'] = _build_task_sections(all_rows, view_as=view_as)
        context['has_any_tasks'] = any(section['rows'] for section in context['task_sections'])
        context['task_rows'] = []
        context['page_obj'] = None

    context['kind_choices'] = TASK_LIST_SECTIONS['student' if view_as == 'student' else 'staff']
    context['today'] = timezone.localdate()
    return render(request, 'tasks/task_list.html', context)


TASK_ACTIVE_STATUSES = (
    Task.Status.TODO,
    Task.Status.DOING,
    Task.Status.BLOCKED,
)


def models_q_status_filter(user, status_filter):
    from django.db.models import Q

    return Q(enrollments__student=user, enrollments__status=status_filter) | Q(
        assignee_type=Task.AssigneeType.GROUP,
        assignee_group_id=user.group_id,
        status=status_filter,
        visibility=Task.Visibility.SHARED,
    )


def models_q_status_filter_staff(status_filter):
    from django.db.models import Q

    return Q(enrollments__status=status_filter) | Q(
        assignee_type=Task.AssigneeType.GROUP,
        status=status_filter,
    )


def models_q_active_filter(user):
    from django.db.models import Q

    q = Q()
    for status in TASK_ACTIVE_STATUSES:
        q |= models_q_status_filter(user, status)
    return q


def models_q_active_filter_staff():
    from django.db.models import Q

    q = Q()
    for status in TASK_ACTIVE_STATUSES:
        q |= models_q_status_filter_staff(status)
    return q


def models_q_finished_filter(user):
    return models_q_status_filter(user, Task.Status.DONE)


def models_q_finished_filter_staff():
    return models_q_status_filter_staff(Task.Status.DONE)


def models_q_student_filter(student_pk):
    from django.db.models import Q

    return Q(enrollments__student_id=student_pk) | Q(
        assignee_type=Task.AssigneeType.USER,
        assignee_user_id=student_pk,
    )


@login_required
def task_create(request):
    if not can_create_tasks(request.user):
        return redirect('tasks:task_list')

    if request.method == 'POST':
        try:
            if user_is_student(request.user):
                task = create_student_task(user=request.user, post=request.POST)
                return redirect('tasks:task_detail', pk=task.pk)
            assign_mode = request.POST.get('assign_mode', 'students')
            if assign_mode == 'group':
                task = create_group_task(user=request.user, post=request.POST)
                messages.success(request, f'Created group task for {task.assignee_group}.')
            else:
                task = create_tasks_bulk(user=request.user, post=request.POST)
                messages.success(request, f'Created task for {task.enrolled_count} student(s).')
            return redirect('tasks:task_detail', pk=task.pk)
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if exc.messages else str(exc))

    context = {
        'form': TaskForm(),
        'action': 'create',
        'subtasks_data': [],
        'is_staff_create': user_is_staff(request.user),
        'visibility_mode': _visibility_form_mode(request.user, creating=True),
        'status_choices': Task.Status.choices,
        'priority_choices': Task.Priority.choices,
    }
    if user_is_staff(request.user):
        context.update(get_assignment_form_context(request.user))
        context.update(resource_container_picker_context(request.user))
        context.update(scheduled_publish_form_defaults())
        context.update({'draft_label': 'draft', 'entity_label': 'task'})
    return render(request, 'tasks/task_form.html', context)


@login_required
def task_detail(request, pk):
    task = _get_task_or_404(request.user, pk)
    user = request.user
    can_content = can_view_task_content(user, task)

    if task.is_group_shared:
        enrollment = None
        if user.role == User.Role.STUDENT and task_allows_subtasks(task) and can_content:
            enrollment = ensure_enrollment_for_subtasks(task, user)
        ctx = {
            'task': task,
            'enrollment': enrollment,
            'view_as': 'staff' if user_is_staff(user) else 'student',
            'can_view_content': can_content,
            'display_title': task.title if can_content else 'Private task',
            'display_status': task.status,
            'can_edit': can_manage_task(user, task),
            'can_delete': can_delete_task(user, task),
            'can_edit_fields': can_edit_task_fields(user, task),
            'can_edit_status': can_change_status(user, task),
            'can_add_update': False,
            'can_comment': False,
            'show_subtasks': task_allows_subtasks(task) and can_content and enrollment is not None,
            'show_updates': False,
            'show_comments': False,
            'status_choices': Task.Status.choices,
            'today': timezone.localdate(),
            **entity_materials_context(user, task),
            **scheduled_publish_detail_context(task),
        }
        if ctx['show_subtasks']:
            ctx.update(_subtask_ctx(user, enrollment))
        return render(request, 'tasks/task_detail.html', ctx)

    if user_is_student(user):
        enrollment = get_enrollment_for_user(user, task)
        if not enrollment:
            raise Http404
        ctx = {
            'task': task,
            'enrollment': enrollment,
            'view_as': 'student',
            'can_view_content': can_content,
            'display_title': task.title if can_content else 'Private task',
            'display_status': enrollment.status,
            'can_edit': can_edit_task(user, task),
            'can_delete': can_delete_task(user, task),
            'can_edit_fields': can_edit_task_fields(user, task),
            'can_edit_status': can_change_status(user, task, enrollment),
            'can_add_update': can_add_update(user, task, enrollment),
            'can_comment': can_comment(user, task, enrollment),
            'show_subtasks': task_allows_subtasks(task) and can_content,
            'show_updates': task_allows_updates(task) and can_content,
            'show_comments': task_allows_comments(task) and can_content,
            'status_choices': Task.Status.choices,
            'today': timezone.localdate(),
            **entity_materials_context(user, task),
            **scheduled_publish_detail_context(task),
        }
        if ctx['show_subtasks']:
            ctx.update(_subtask_ctx(user, enrollment))
        if ctx['show_updates']:
            ctx['updates'] = enrollment.updates.select_related('author')
        if ctx['show_comments']:
            ctx['comment_tree'] = build_comment_tree(enrollment)
        _apply_feedback_context(ctx, target=enrollment, viewer=user)
        return render(request, 'tasks/task_detail.html', ctx)

    enrollments = (
        get_visible_enrollments_for_user(user, task=task)
        .prefetch_related('subtask_enrollments', 'updates', 'comments')
        .order_by('student__display_name')
    )
    template_subtask_models = list(
        task.subtasks.filter(added_by__isnull=True).order_by('order', 'pk')
    )
    owner_enrollment = None
    if is_personal_task(task):
        owner_enrollment = enrollments.filter(student_id=task.assignee_user_id).first()
    enrollment_rows = []
    for enrollment in enrollments:
        sync_subtask_enrollments(enrollment)
        status_map = _subtask_status_map(enrollment)
        if is_personal_task(task):
            subtask_list = list(
                enrollment.subtasks_for_student().order_by('order', 'pk')
            )
            subtask_rows = [
                _subtask_row(user, enrollment, st, status_map, readonly=True)
                for st in subtask_list
            ]
        else:
            subtask_rows = [
                _subtask_row(user, enrollment, st, status_map)
                for st in template_subtask_models
            ]
        row = {
            'enrollment': enrollment,
            'subtasks': subtask_rows,
            'can_edit_status': can_change_status(user, task, enrollment),
        }
        feedback_ctx = build_section_context(target=enrollment, viewer=user)
        if feedback_ctx:
            row['feedback'] = feedback_ctx
        enrollment_rows.append(row)

    ctx = {
        'task': task,
        'view_as': 'staff',
        'enrollment': None,
        'enrollment_rows': enrollment_rows,
        'template_subtask_models': (
            list(owner_enrollment.subtasks_for_student().order_by('order', 'pk'))
            if owner_enrollment
            else template_subtask_models
        ),
        'can_view_content': can_content,
        'display_title': task.title if can_content else 'Private task',
        'display_status': task.status,
        'can_edit': can_edit_task(user, task),
        'can_delete': can_delete_task(user, task),
        'can_edit_fields': can_edit_task_fields(user, task),
        'can_add_enrollment': can_add_enrollment(user, task),
        'can_edit_status': False,
        'can_add_update': False,
        'can_comment': False,
        'show_subtasks': task_allows_subtasks(task),
        'show_updates': False,
        'show_comments': False,
        'status_choices': Task.Status.choices,
        'today': timezone.localdate(),
    }
    if can_add_enrollment(user, task):
        ctx.update(get_assignment_form_context(user))
    if ctx['show_subtasks'] and can_content:
        if is_personal_task(task) and owner_enrollment:
            ctx.update(_subtask_ctx_for_staff_personal(user, owner_enrollment))
        else:
            staff_items = []
            for st in template_subtask_models:
                staff_items.append({
                    'subtask': st,
                    'display_status': Task.Status.TODO,
                    'can_change_status': False,
                    'can_edit': can_edit_subtask(user, st),
                    'can_delete': can_delete_subtask(user, st),
                })
            ctx.update({
                'template_subtasks': staff_items,
                'participant_subtasks': [],
                'subtask_done': 0,
                'subtask_total': len(staff_items),
                'can_add_template_subtask': can_add_template_subtask(user, task),
                'can_add_participant_subtask': False,
                'show_staff_subtasks': True,
            })
    ctx.update(entity_materials_context(user, task))
    ctx.update(scheduled_publish_detail_context(task))
    return render(request, 'tasks/task_detail.html', ctx)


@login_required
def task_edit(request, pk):
    task = _get_task_or_404(request.user, pk)
    if not can_edit_task(request.user, task):
        raise Http404

    enrollment = None
    show_status = not task.is_group_shared
    show_toggles = can_edit_task_fields(request.user, task) or user_is_staff(request.user)
    if user_is_student(request.user):
        enrollment = get_enrollment_for_user(request.user, task)
    elif is_staff_assigned(task) and not task.is_group_shared:
        show_status = False

    if request.method == 'POST':
        form = TaskForm(
            request.POST,
            instance=task,
            enrollment=enrollment,
            show_status=show_status and enrollment is not None,
            show_toggles=show_toggles,
        )
        if task.is_group_shared:
            form.fields['status'] = django_forms.ChoiceField(
                choices=Task.Status.choices,
                required=False,
                initial=task.status,
            )
        if form.is_valid():
            old_visibility = task.visibility
            form.save()
            task.refresh_from_db()
            if is_staff_assigned(task):
                from accounts.models import User

                students = User.objects.filter(
                    pk__in=task.enrollments.values_list('student_id', flat=True),
                    role=User.Role.STUDENT,
                    is_active=True,
                )
                apply_publish_schedule_from_post(
                    entity=task,
                    post=request.POST,
                    actor=request.user,
                    previous_visibility=old_visibility,
                    students=students,
                )
                apply_entity_resource_container(
                    entity=task,
                    user=request.user,
                    post=request.POST,
                    assignee_group=task.assignee_group,
                )
            if enrollment and 'status' in form.cleaned_data:
                enrollment.status = form.cleaned_data['status']
                enrollment.save(update_fields=['status', 'completed_at'])
                if (
                    enrollment.status == Task.Status.DONE
                    and user_is_student(request.user)
                ):
                    notify_student_task_completed(student=request.user, task=task)
            elif task.is_group_shared and 'status' in form.cleaned_data:
                task.status = form.cleaned_data['status']
                task.save(update_fields=['status', 'completed_at'])
            messages.success(request, 'Task updated.')
            return redirect('tasks:task_detail', pk=task.pk)
    else:
        form = TaskForm(
            instance=task,
            enrollment=enrollment,
            show_status=show_status and enrollment is not None,
            show_toggles=show_toggles,
        )
        if task.is_group_shared:
            form.fields['status'] = django_forms.ChoiceField(
                choices=Task.Status.choices,
                required=False,
                initial=task.status,
            )

    context = {
        'form': form,
        'action': 'edit',
        'task': task,
        'subtasks_data': [],
        'is_staff_create': False,
        'visibility_mode': _visibility_form_mode(request.user, task=task),
        'status_choices': Task.Status.choices,
        'priority_choices': Task.Priority.choices,
    }
    if is_staff_assigned(task):
        context.update(
            resource_container_picker_context(
                request.user,
                entity_title=task.title,
                linked_container=task.resource_container,
            ),
        )
        context.update(scheduled_publish_picker_context(task))
        context.update({'draft_label': 'draft', 'entity_label': 'task'})
    return render(request, 'tasks/task_form.html', context)


@login_required
def task_delete(request, pk):
    task = _get_task_or_404(request.user, pk)
    if not can_delete_task(request.user, task):
        return HttpResponseForbidden()
    if request.method == 'POST':
        cancel_scheduled_publish(task, save=False)
        task.delete()
        messages.success(request, 'Task deleted.')
        return redirect('tasks:task_list')
    return render(request, 'tasks/task_confirm_delete.html', {'task': task})


@login_required
@require_POST
def task_quick_status(request, pk):
    task = _get_task_or_404(request.user, pk)
    status = request.POST.get('status')
    if status not in Task.Status.values:
        return HttpResponseForbidden()

    if task.is_group_shared:
        if not can_change_status(request.user, task):
            return HttpResponseForbidden()
        task.status = status
        task.save(update_fields=['status', 'completed_at'])
        enrollment = None
    else:
        enrollment = get_enrollment_for_user(request.user, task)
        if not enrollment or not can_change_status(request.user, task, enrollment):
            return HttpResponseForbidden()
        enrollment.status = status
        enrollment.save(update_fields=['status', 'completed_at'])
        if status == Task.Status.DONE and user_is_student(request.user):
            notify_student_task_completed(student=request.user, task=task)

    ctx = _task_status_context(request.user, task, enrollment)
    if request.GET.get('inline') == 'list':
        ctx['status_compact'] = True
        ctx['status_url_suffix'] = '?inline=list'
        return render(request, 'tasks/_task_list_status_cell.html', ctx)
    return render(request, 'tasks/_task_status_section.html', ctx)


@login_required
@require_POST
def subtask_status(request, pk):
    subtask = get_object_or_404(Subtask.objects.select_related('task'), pk=pk)
    task = subtask.task
    if not can_view_task(request.user, task):
        raise Http404

    status = request.POST.get('status')
    if status not in Task.Status.values:
        return HttpResponseForbidden()

    if task.is_group_shared and user_is_student(request.user):
        enrollment = ensure_enrollment_for_subtasks(task, request.user)
    else:
        enrollment = get_enrollment_for_user(request.user, task)

    if not enrollment or not can_change_subtask_status(request.user, enrollment, subtask):
        return HttpResponseForbidden()

    set_subtask_status(enrollment, subtask, status)
    enrollment = TaskEnrollment.objects.prefetch_related(
        'subtask_enrollments',
        'task__subtasks',
    ).get(pk=enrollment.pk)
    ctx = _subtask_ctx(request.user, enrollment)
    ctx.update({
        'task': task,
        'enrollment': enrollment,
        'show_subtasks': task_allows_subtasks(task),
    })
    return render(request, 'tasks/_subtasks_section.html', ctx)


@login_required
def update_create(request, pk):
    task = _get_task_or_404(request.user, pk)
    enrollment = get_enrollment_for_user(request.user, task)
    if not enrollment or not can_add_update(request.user, task, enrollment):
        raise Http404

    if request.method == 'POST':
        form = TaskUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.enrollment = enrollment
            update.author = request.user
            update.save()
            return redirect('tasks:task_detail', pk=task.pk)
    else:
        form = TaskUpdateForm()

    return render(request, 'tasks/update_form.html', {
        'form': form,
        'task': task,
    })


@login_required
def comment_create(request, pk):
    task = _get_task_or_404(request.user, pk)
    enrollment = get_enrollment_for_user(request.user, task)
    if not enrollment or not can_comment(request.user, task, enrollment):
        raise Http404

    if request.method == 'POST':
        form = TaskCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.enrollment = enrollment
            comment.author = request.user
            comment.save()
            return redirect('tasks:task_detail', pk=task.pk)
    else:
        form = TaskCommentForm()

    return render(request, 'tasks/comment_form.html', {
        'form': form,
        'task': task,
        'heading': 'Add comment',
    })


@login_required
def comment_reply_create(request, comment_pk):
    parent = get_object_or_404(
        TaskComment.objects.select_related('enrollment__task'),
        pk=comment_pk,
    )
    task = parent.enrollment.task
    enrollment = parent.enrollment
    if not can_comment(request.user, task, enrollment):
        raise Http404

    if request.method == 'POST':
        form = TaskCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.enrollment = enrollment
            comment.author = request.user
            comment.parent = parent
            comment.save()
            return redirect('tasks:task_detail', pk=task.pk)
    else:
        form = TaskCommentForm()

    return render(request, 'tasks/comment_form.html', {
        'form': form,
        'task': task,
        'parent_comment': parent,
        'heading': 'Reply',
    })


@login_required
def subtask_create(request, pk):
    task = _get_task_or_404(request.user, pk)
    template_mode = can_add_template_subtask(request.user, task)
    enrollment = None

    if template_mode:
        pass
    else:
        enrollment = get_enrollment_for_user(request.user, task)
        if not enrollment or not can_add_participant_subtask(request.user, task, enrollment):
            raise Http404

    if request.method == 'POST':
        form = SubtaskForm(request.POST)
        if form.is_valid():
            subtask = form.save(commit=False)
            subtask.task = task
            if template_mode:
                subtask.order = task.subtasks.filter(added_by__isnull=True).count()
                subtask.added_by = None
                subtask.save()
                for task_enrollment in task.enrollments.all():
                    sync_subtask_enrollments(task_enrollment)
            else:
                subtask.order = task.subtasks.filter(added_by=enrollment.student).count()
                subtask.added_by = enrollment.student
                subtask.save()
                set_subtask_status(enrollment, subtask, Task.Status.TODO)
            messages.success(request, 'Subtask added.')
            return redirect('tasks:task_detail', pk=task.pk)
    else:
        form = SubtaskForm()

    return render(request, 'tasks/subtask_form.html', {
        'form': form,
        'task': task,
        'action': 'create',
        'is_template': template_mode,
    })


@login_required
def participant_subtask_create(request, pk):
    return subtask_create(request, pk)


@login_required
def subtask_edit(request, pk):
    subtask = get_object_or_404(Subtask.objects.select_related('task'), pk=pk)
    task = subtask.task
    if not can_view_task(request.user, task):
        raise Http404
    if not can_edit_subtask(request.user, subtask):
        raise Http404

    if request.method == 'POST':
        form = SubtaskForm(request.POST, instance=subtask)
        if form.is_valid():
            form.save()
            for enrollment in task.enrollments.all():
                sync_subtask_enrollments(enrollment)
            messages.success(request, 'Subtask updated.')
            return redirect('tasks:task_detail', pk=task.pk)
    else:
        form = SubtaskForm(instance=subtask)

    return render(request, 'tasks/subtask_form.html', {
        'form': form,
        'task': task,
        'subtask': subtask,
        'action': 'edit',
        'is_template': subtask.is_template,
    })


@login_required
def subtask_delete(request, pk):
    subtask = get_object_or_404(Subtask.objects.select_related('task'), pk=pk)
    task = subtask.task
    if not can_view_task(request.user, task):
        raise Http404
    if not can_delete_subtask(request.user, subtask):
        return HttpResponseForbidden()

    if request.method == 'POST':
        subtask.delete()
        messages.success(request, 'Subtask deleted.')
        return redirect('tasks:task_detail', pk=task.pk)

    return render(request, 'tasks/subtask_confirm_delete.html', {
        'task': task,
        'subtask': subtask,
    })


@login_required
@require_POST
def task_add_enrollment(request, pk):
    task = _get_task_or_404(request.user, pk)
    try:
        count = add_task_enrollments(user=request.user, task=task, post=request.POST)
        messages.success(request, f'Added {count} student(s) to this task.')
    except ValidationError as exc:
        messages.error(request, exc.messages[0] if exc.messages else str(exc))
    return redirect('tasks:task_detail', pk=task.pk)
