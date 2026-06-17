from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.notifications.staff_events import notify_student_goal_completed
from cohorts.permissions import (
    get_teacher_accessible_students,
    user_is_admin,
    user_is_staff,
    user_is_student,
)

from config.form_widgets import resolve_form_date
from feedback.services import build_section_context

from config.entity_publish import (
    apply_publish_schedule_from_post,
    cancel_scheduled_publish,
    scheduled_publish_detail_context,
    scheduled_publish_form_defaults,
    scheduled_publish_picker_context,
)
from resources.entity_links import apply_entity_resource_container, entity_materials_context, resource_container_picker_context

from .forms import GoalForm
from .models import Goal, GoalEnrollment, Milestone
from .permissions import (
    can_create_goals,
    can_delete_goal,
    can_edit_goal,
    can_mark_achieved,
    can_reactivate_enrollment,
    can_toggle_milestone,
    can_view_goal,
    get_enrollment_for_user,
    get_visible_enrollments_for_user,
    get_visible_goals_for_user,
    is_staff_assigned,
)
from .services import (
    create_goals_bulk,
    create_student_goal,
    get_assignment_form_context,
    normalize_milestone_title,
    sync_enrollment_status_from_milestones,
    sync_milestones,
    toggle_milestone_completion,
)


def _goal_queryset():
    return (
        Goal.objects.select_related('author', 'created_by', 'resource_container')
        .prefetch_related(
            'milestones',
            Prefetch(
                'enrollments',
                queryset=GoalEnrollment.objects.select_related('student', 'student__group'),
            ),
        )
    )


def _get_goal_or_404(user, pk):
    goal = get_object_or_404(_goal_queryset(), pk=pk)
    if not can_view_goal(user, goal):
        raise Http404
    return goal


def _get_enrollment_or_404(user, enrollment_pk):
    enrollment = get_object_or_404(
        GoalEnrollment.objects.select_related('goal', 'student', 'student__group'),
        pk=enrollment_pk,
    )
    if not can_view_goal(user, enrollment.goal):
        raise Http404
    return enrollment


def _goal_progress_ctx(user, enrollment):
    goal = enrollment.goal
    completed_ids = enrollment.completed_milestone_ids()
    milestones = [
        {'milestone': ms, 'completed': ms.pk in completed_ids}
        for ms in goal.milestones.all()
    ]
    return {
        'goal': goal,
        'enrollment': enrollment,
        'milestones': milestones,
        'can_toggle_milestone': can_toggle_milestone(user, enrollment),
        'can_mark_achieved': can_mark_achieved(user, enrollment),
        'can_reactivate': can_reactivate_enrollment(user, enrollment),
    }


def _apply_feedback_context(ctx, *, target, viewer):
    feedback_ctx = build_section_context(target=target, viewer=viewer)
    if feedback_ctx:
        ctx.update(feedback_ctx)
        ctx['show_feedback'] = True
    else:
        ctx['show_feedback'] = False
    return ctx


def _visibility_form_mode(user, *, goal=None, creating=False):
    if creating:
        return 'staff' if user_is_staff(user) else 'student'
    if goal and user_is_staff(user) and is_staff_assigned(goal):
        return 'staff'
    return 'student'


def _build_list_items(goals, *, user, filtered_student=None):
    items = []
    for goal in goals:
        if user_is_student(user):
            enrollment = get_enrollment_for_user(user, goal)
        elif filtered_student:
            enrollment = goal.enrollments.filter(student=filtered_student).first()
        else:
            enrollment = None
        items.append({'goal': goal, 'enrollment': enrollment})
    return items


@login_required
def goal_list(request):
    user = request.user
    status_filter = request.GET.get('status', '')
    qs = get_visible_goals_for_user(user)

    if status_filter:
        if user_is_student(user):
            qs = qs.filter(enrollments__student=user, enrollments__status=status_filter)
        else:
            qs = qs.filter(enrollments__status=status_filter)

    if user_is_student(user):
        visible = get_visible_goals_for_user(user)
        enrollments = GoalEnrollment.objects.filter(
            goal__in=visible,
            student=user,
        )
        context = {
            'status_filter': status_filter,
            'total': enrollments.count(),
            'in_progress': enrollments.filter(status=GoalEnrollment.Status.IN_PROGRESS).count(),
            'completed': enrollments.filter(status=GoalEnrollment.Status.COMPLETED).count(),
            'view_as': 'student',
            'status_choices': GoalEnrollment.Status.choices,
            'can_create': can_create_goals(user),
        }
        filtered_student = None
    else:
        student_pk = request.GET.get('student', '')
        if student_pk:
            qs = qs.filter(enrollments__student_id=student_pk)
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
            'status_choices': GoalEnrollment.Status.choices,
            'view_as': 'admin' if user_is_admin(user) else 'teacher',
            'can_create': can_create_goals(user),
        }

    qs = qs.distinct()
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    context['goals'] = _build_list_items(page_obj, user=user, filtered_student=filtered_student)
    context['page_obj'] = page_obj
    return render(request, 'goals/goal_list.html', context)


@login_required
def goal_create(request):
    if not can_create_goals(request.user):
        return redirect('goals:list')

    form = GoalForm()
    if request.method == 'POST':
        form = GoalForm(request.POST)
        try:
            if user_is_student(request.user):
                goal = create_student_goal(user=request.user, post=request.POST)
                return redirect('goals:detail', pk=goal.pk)
            goal = create_goals_bulk(user=request.user, post=request.POST)
            count = goal.enrolled_count
            messages.success(request, f'Created goal for {count} student(s).')
            return redirect('goals:detail', pk=goal.pk)
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if exc.messages else str(exc))

    context = {
        'form': form,
        'action': 'create',
        'milestones_data': [],
        'target_date_display': resolve_form_date(form, 'target_date'),
        'is_staff_create': user_is_staff(request.user),
        'visibility_mode': _visibility_form_mode(request.user, creating=True),
    }
    if user_is_staff(request.user):
        context.update(get_assignment_form_context(request.user))
        context.update(resource_container_picker_context(request.user))
        context.update(scheduled_publish_form_defaults())
        context.update({'draft_label': 'draft', 'entity_label': 'goal'})
    return render(request, 'goals/goal_form.html', context)


@login_required
def goal_detail(request, pk):
    goal = _get_goal_or_404(request.user, pk)
    user = request.user

    if user_is_student(user):
        enrollment = get_enrollment_for_user(user, goal)
        if not enrollment:
            raise Http404
        ctx = {
            'goal': goal,
            'view_as': 'student',
            'can_edit': can_edit_goal(user, goal),
            'can_delete': can_delete_goal(user, goal),
            **entity_materials_context(user, goal),
            **scheduled_publish_detail_context(goal),
        }
        ctx.update(_goal_progress_ctx(user, enrollment))
        _apply_feedback_context(ctx, target=enrollment, viewer=user)
        return render(request, 'goals/goal_detail.html', ctx)

    enrollments = (
        get_visible_enrollments_for_user(user, goal=goal)
        .prefetch_related('milestone_completions')
        .order_by('student__display_name')
    )
    enrollment_rows = []
    milestones = list(goal.milestones.all())
    for enrollment in enrollments:
        completed_ids = enrollment.completed_milestone_ids()
        row = {
            'enrollment': enrollment,
            'milestones': [
                {'milestone': ms, 'completed': ms.pk in completed_ids}
                for ms in milestones
            ],
            'can_reactivate': can_reactivate_enrollment(user, enrollment),
        }
        feedback_ctx = build_section_context(target=enrollment, viewer=user)
        if feedback_ctx:
            row['feedback'] = feedback_ctx
        enrollment_rows.append(row)

    ctx = {
        'goal': goal,
        'view_as': 'staff',
        'enrollment_rows': enrollment_rows,
        'milestones': milestones,
        'can_edit': can_edit_goal(user, goal),
        'can_delete': can_delete_goal(user, goal),
        **entity_materials_context(user, goal),
        **scheduled_publish_detail_context(goal),
    }
    return render(request, 'goals/goal_detail.html', ctx)


@login_required
def goal_edit(request, pk):
    goal = _get_goal_or_404(request.user, pk)
    if not can_edit_goal(request.user, goal):
        raise Http404

    enrollment = None
    show_status = True
    if user_is_student(request.user):
        enrollment = get_enrollment_for_user(request.user, goal)
    elif is_staff_assigned(goal):
        show_status = False

    if request.method == 'POST':
        form = GoalForm(
            request.POST,
            instance=goal,
            enrollment=enrollment,
            show_status=show_status,
        )
        if form.is_valid():
            old_visibility = goal.visibility
            form.save()
            goal.refresh_from_db()
            sync_milestones(goal, request.POST)
            if is_staff_assigned(goal):
                students = User.objects.filter(
                    pk__in=goal.enrollments.values_list('student_id', flat=True),
                    role=User.Role.STUDENT,
                    is_active=True,
                )
                apply_publish_schedule_from_post(
                    entity=goal,
                    post=request.POST,
                    actor=request.user,
                    previous_visibility=old_visibility,
                    students=students,
                )
                apply_entity_resource_container(
                    entity=goal,
                    user=request.user,
                    post=request.POST,
                    assignee_group=None,
                )
            if enrollment and 'status' in form.fields:
                enrollment.status = form.cleaned_data['status']
                enrollment.save(update_fields=['status'])
            messages.success(request, 'Goal updated.')
            return redirect('goals:detail', pk=goal.pk)
    else:
        form = GoalForm(instance=goal, enrollment=enrollment, show_status=show_status)

    context = {
        'form': form,
        'action': 'edit',
        'goal': goal,
        'target_date_display': resolve_form_date(form, 'target_date', instance=goal),
        'milestones_data': [
            normalize_milestone_title(title)
            for title in goal.milestones.order_by('order', 'pk').values_list('title', flat=True)
        ],
        'is_staff_create': False,
        'visibility_mode': _visibility_form_mode(request.user, goal=goal),
    }
    if is_staff_assigned(goal):
        context.update(
            resource_container_picker_context(
                request.user,
                entity_title=goal.title,
                linked_container=goal.resource_container,
            ),
        )
        context.update(scheduled_publish_picker_context(goal))
        context.update({'draft_label': 'draft', 'entity_label': 'goal'})
    return render(request, 'goals/goal_form.html', context)


@login_required
def goal_delete(request, pk):
    goal = _get_goal_or_404(request.user, pk)
    if not can_delete_goal(request.user, goal):
        return HttpResponseForbidden()
    if request.method == 'POST':
        cancel_scheduled_publish(goal, save=False)
        goal.delete()
        messages.success(request, 'Goal deleted.')
        return redirect('goals:list')
    return render(request, 'goals/goal_confirm_delete.html', {'goal': goal})


@login_required
@require_POST
def goal_mark_achieved(request, pk):
    goal = _get_goal_or_404(request.user, pk)
    enrollment = get_enrollment_for_user(request.user, goal)
    if not enrollment or not can_mark_achieved(request.user, enrollment):
        messages.error(request, 'Complete all milestones before marking this goal as achieved.')
        return redirect('goals:detail', pk=goal.pk)
    enrollment.status = GoalEnrollment.Status.COMPLETED
    enrollment.achieved_at = timezone.now()
    enrollment.save(update_fields=['status', 'achieved_at'])
    if request.user.role == User.Role.STUDENT:
        notify_student_goal_completed(student=request.user, goal=goal)
    messages.success(request, 'Goal marked as achieved.')
    return redirect('goals:detail', pk=goal.pk)


@login_required
@require_POST
def goal_reactivate(request, pk):
    goal = _get_goal_or_404(request.user, pk)
    enrollment = get_enrollment_for_user(request.user, goal)
    if not enrollment or not can_reactivate_enrollment(request.user, enrollment):
        return HttpResponseForbidden()
    enrollment.achieved_at = None
    sync_enrollment_status_from_milestones(enrollment)
    messages.success(request, 'Goal reactivated.')
    return redirect('goals:detail', pk=goal.pk)


@login_required
@require_POST
def enrollment_reactivate(request, enrollment_pk):
    enrollment = _get_enrollment_or_404(request.user, enrollment_pk)
    if not can_reactivate_enrollment(request.user, enrollment):
        return HttpResponseForbidden()
    enrollment.achieved_at = None
    sync_enrollment_status_from_milestones(enrollment)
    messages.success(request, f'Reactivated goal for {enrollment.student.display_name}.')
    return redirect('goals:detail', pk=enrollment.goal_id)


@login_required
@require_POST
def milestone_toggle(request, pk):
    milestone = get_object_or_404(Milestone.objects.select_related('goal'), pk=pk)
    goal = milestone.goal
    if not can_view_goal(request.user, goal):
        raise Http404
    enrollment = get_enrollment_for_user(request.user, goal)
    if not enrollment or not can_toggle_milestone(request.user, enrollment):
        return HttpResponseForbidden()
    toggle_milestone_completion(enrollment, milestone)
    enrollment = GoalEnrollment.objects.prefetch_related(
        'milestone_completions',
        'goal__milestones',
    ).get(pk=enrollment.pk)
    return render(request, 'goals/_goal_progress.html', _goal_progress_ctx(request.user, enrollment))
