from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.notifications.staff_events import maybe_notify_workflow_completed
from cohorts.permissions import user_is_staff, user_is_student

from .forms import WorkflowMetadataForm, WorkflowStepForm
from .models import StepCompletion, Workflow, WorkflowEnrollment, WorkflowStep
from .permissions import (
    build_step_data,
    can_create_workflow,
    can_manage_workflow,
    can_toggle_step,
    can_view_workflow,
    get_visible_workflows_for_user,
    shared_progress_pct,
)
from resources.entity_links import entity_materials_context, resource_container_picker_context

from .services import (
    create_workflow,
    get_assignment_form_context,
    update_workflow_assignment,
    update_workflow_metadata,
)


def _get_workflow_or_404(user, pk):
    workflow = get_object_or_404(
        Workflow.objects.select_related(
            'created_by', 'assignee_cohort', 'assignee_group', 'assignee_group__cohort',
            'resource_container',
        ).prefetch_related('steps', 'completions'),
        pk=pk,
    )
    if not can_view_workflow(user, workflow):
        raise Http404
    return workflow


@login_required
def workflow_list(request):
    user = request.user
    if user_is_student(user):
        visible = get_visible_workflows_for_user(user)
        individual = visible.filter(progress_mode=Workflow.ProgressMode.INDIVIDUAL).prefetch_related(
            'steps', 'enrollments__student', 'completions',
        )
        shared = visible.filter(progress_mode=Workflow.ProgressMode.SHARED).prefetch_related(
            'steps', 'completions',
        )
        enrollment_map = {
            e.workflow_id: e
            for e in WorkflowEnrollment.objects.filter(
                student=user, workflow__in=individual,
            ).select_related('workflow')
        }
        individual_rows = []
        for workflow in individual:
            enrollment = enrollment_map.get(workflow.pk)
            if enrollment:
                individual_rows.append({
                    'workflow': workflow,
                    'progress': enrollment.progress_pct(),
                    'enrollment': enrollment,
                })
        shared_rows = [
            {
                'workflow': workflow,
                'progress': shared_progress_pct(workflow),
                'enrollment': None,
            }
            for workflow in shared
        ]
        context = {
            'view_as': 'student',
            'rows': individual_rows + shared_rows,
        }
    else:
        workflows = get_visible_workflows_for_user(user).prefetch_related('steps', 'enrollments')
        context = {
            'view_as': 'staff',
            'workflows': workflows,
            'can_create': can_create_workflow(user),
        }
    return render(request, 'workflows/list.html', context)


@login_required
def workflow_create(request):
    if not can_create_workflow(request.user):
        return redirect('workflows:list')

    if request.method == 'POST':
        try:
            workflow = create_workflow(user=request.user, post=request.POST)
            messages.success(request, f'Workflow "{workflow.title}" created.')
            return redirect('workflows:detail', pk=workflow.pk)
        except ValidationError as exc:
            message = exc.messages[0] if getattr(exc, 'messages', None) else str(exc)
            messages.error(request, message)

    context = {
        'editing': False,
        'workflow': None,
        **get_assignment_form_context(request.user),
        **resource_container_picker_context(request.user),
    }
    return render(request, 'workflows/form.html', context)


@login_required
def workflow_detail(request, pk):
    workflow = _get_workflow_or_404(request.user, pk)
    user = request.user

    if user_is_student(user):
        if not can_toggle_step(user, workflow):
            return render(request, 'workflows/detail.html', {
                'workflow': workflow,
                'view_as': 'student',
                'not_assigned': True,
            })
        progress = (
            shared_progress_pct(workflow)
            if workflow.is_shared
            else WorkflowEnrollment.objects.get(workflow=workflow, student=user).progress_pct()
        )
        context = {
            'workflow': workflow,
            'view_as': 'student',
            'step_data': build_step_data(user, workflow),
            'progress': progress,
            'can_toggle': True,
            **entity_materials_context(user, workflow),
        }
    else:
        enrollments = (
            WorkflowEnrollment.objects.filter(workflow=workflow)
            .select_related('student')
        )
        from .permissions import get_workflow_assigned_students

        assigned_students = get_workflow_assigned_students(workflow)
        enrolled_ids = set(workflow.enrollments.values_list('student_id', flat=True))
        if workflow.progress_mode == Workflow.ProgressMode.INDIVIDUAL:
            from cohorts.permissions import (
                get_active_students_for_cohort,
                get_active_students_for_group,
                get_teacher_group_ids,
                user_is_admin,
            )

            if workflow.assignee_type == Workflow.AssigneeType.COHORT:
                pool = get_active_students_for_cohort(workflow.assignee_cohort)
            else:
                pool = get_active_students_for_group(workflow.assignee_group)
            if not user_is_admin(user):
                pool = pool.filter(group_id__in=get_teacher_group_ids(user))
            available_students = pool.exclude(pk__in=enrolled_ids)
        else:
            available_students = User.objects.none()

        context = {
            'workflow': workflow,
            'view_as': 'staff',
            'can_manage': can_manage_workflow(user, workflow),
            'step_data': build_step_data(user, workflow) if workflow.is_shared else None,
            'shared_progress': shared_progress_pct(workflow) if workflow.is_shared else None,
            'enrollments': enrollments,
            'assigned_count': assigned_students.count(),
            'available_students': available_students,
            **entity_materials_context(user, workflow),
        }

    return render(request, 'workflows/detail.html', context)


@login_required
def workflow_edit(request, pk):
    workflow = _get_workflow_or_404(request.user, pk)
    if not can_manage_workflow(request.user, workflow):
        return HttpResponseForbidden('You cannot edit this workflow.')

    if request.method == 'POST':
        section = request.POST.get('form_section', 'metadata')
        try:
            if section == 'assignment':
                update_workflow_assignment(workflow=workflow, user=request.user, post=request.POST)
                messages.success(request, 'Assignment updated.')
            else:
                update_workflow_metadata(workflow=workflow, user=request.user, post=request.POST)
                messages.success(request, 'Workflow updated.')
            return redirect('workflows:detail', pk=workflow.pk)
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if exc.messages else str(exc))

    enrolled_ids = list(workflow.enrollments.values_list('student_id', flat=True))
    context = {
        'editing': True,
        'workflow': workflow,
        'metadata_form': WorkflowMetadataForm(instance=workflow),
        'enrolled_ids': enrolled_ids,
        **get_assignment_form_context(request.user),
        **resource_container_picker_context(
            request.user,
            entity_title=workflow.title,
            linked_container=workflow.resource_container,
        ),
    }
    return render(request, 'workflows/form.html', context)


@login_required
def workflow_delete(request, pk):
    workflow = _get_workflow_or_404(request.user, pk)
    if not can_manage_workflow(request.user, workflow):
        return HttpResponseForbidden()
    if request.method == 'POST':
        workflow.delete()
        messages.success(request, 'Workflow deleted.')
        return redirect('workflows:list')
    return render(request, 'workflows/confirm_delete.html', {'workflow': workflow})


@login_required
@require_POST
def step_add(request, workflow_pk):
    workflow = get_object_or_404(Workflow, pk=workflow_pk)
    if not can_view_workflow(request.user, workflow) or not can_manage_workflow(request.user, workflow):
        raise Http404
    form = WorkflowStepForm(request.POST)
    if form.is_valid():
        step = form.save(commit=False)
        step.workflow = workflow
        max_order = workflow.steps.aggregate(max_order=Max('order'))['max_order'] or 0
        step.order = max_order + 1
        step.save()
    else:
        messages.error(request, 'Could not add step. Check the title and try again.')
    return redirect('workflows:detail', pk=workflow_pk)


@login_required
@require_POST
def step_delete(request, pk):
    step = get_object_or_404(WorkflowStep.objects.select_related('workflow'), pk=pk)
    workflow = step.workflow
    if not can_view_workflow(request.user, workflow) or not can_manage_workflow(request.user, workflow):
        raise Http404
    workflow_pk = step.workflow_id
    step.delete()
    return redirect('workflows:detail', pk=workflow_pk)


@login_required
@require_POST
def step_toggle(request, step_pk):
    step = get_object_or_404(WorkflowStep.objects.select_related('workflow'), pk=step_pk)
    workflow = step.workflow
    if not can_toggle_step(request.user, workflow):
        return HttpResponseForbidden()

    steps = list(workflow.steps.all())
    done_ids = set()
    if workflow.is_shared:
        done_ids = set(
            workflow.completions.filter(student__isnull=True).values_list('step_id', flat=True)
        )
    else:
        done_ids = set(
            workflow.completions.filter(student=request.user).values_list('step_id', flat=True)
        )

    step_index = next(i for i, s in enumerate(steps) if s.pk == step.pk)
    locked = (
        step.requires_previous
        and step_index > 0
        and steps[step_index - 1].pk not in done_ids
    )
    if locked:
        return HttpResponseForbidden('Complete the previous step first.')

    student = None if workflow.is_shared else request.user
    completion = StepCompletion.objects.filter(
        workflow=workflow, step=step, student=student,
    ).first()
    if completion:
        completion.delete()
    else:
        StepCompletion.objects.create(
            workflow=workflow,
            step=step,
            student=student,
            completed_by=request.user,
        )
        if user_is_student(request.user):
            maybe_notify_workflow_completed(workflow=workflow, student=request.user)

    return redirect('workflows:detail', pk=workflow.pk)


@login_required
@require_POST
def enroll_student(request, workflow_pk):
    workflow = _get_workflow_or_404(request.user, workflow_pk)
    if not can_manage_workflow(request.user, workflow):
        return HttpResponseForbidden()
    if workflow.is_shared:
        return HttpResponseForbidden('Shared workflows do not use enrollments.')
    student_id = request.POST.get('student_id')
    if student_id:
        from .permissions import can_assign_students

        student = get_object_or_404(User, pk=student_id, role=User.Role.STUDENT)
        if can_assign_students(request.user, workflow, [student]):
            enrollment, created = WorkflowEnrollment.objects.get_or_create(
                workflow=workflow,
                student=student,
            )
            if created:
                from accounts.notifications.scheduling import schedule_workflow_assigned

                schedule_workflow_assigned(
                    workflow=workflow,
                    students=[student],
                    actor=request.user,
                )
    return redirect('workflows:detail', pk=workflow_pk)


@login_required
@require_POST
def unenroll_student(request, workflow_pk, student_pk):
    workflow = _get_workflow_or_404(request.user, workflow_pk)
    if not can_manage_workflow(request.user, workflow):
        return HttpResponseForbidden()
    StepCompletion.objects.filter(workflow=workflow, student_id=student_pk).delete()
    WorkflowEnrollment.objects.filter(workflow=workflow, student_id=student_pk).delete()
    return redirect('workflows:detail', pk=workflow_pk)
