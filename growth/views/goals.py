from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..forms import GoalForm, GoalSubgoalForm, TeacherGoalForm
from ..models import Goal, GoalSubgoal
from ..selectors import get_students_for_teacher, get_visible_goals_for_user
from ..services.permissions import (
    can_delete_goal,
    can_delete_subgoal,
    can_edit_goal,
    can_edit_subgoal,
    can_manage_goal_subgoals,
    can_mark_goal_achieved,
    can_toggle_subgoal,
    can_view_goal,
)
from tracker.permissions import user_is_student, user_is_teacher, user_is_admin


def _get_goal_or_404(user, pk):
    goal = get_object_or_404(Goal.objects.select_related('student', 'created_by'), pk=pk)
    if not can_view_goal(user, goal):
        raise Http404
    return goal


@login_required
def goal_list(request):
    goals = get_visible_goals_for_user(request.user)
    can_create = user_is_student(request.user) or user_is_teacher(request.user)
    context = {
        'goals': goals,
        'is_student': user_is_student(request.user),
        'can_create': can_create,
    }
    return render(request, 'growth/goals/goal_list.html', context)


@login_required
def goal_create(request):
    user = request.user

    if user_is_teacher(user) or user_is_admin(user):
        student_qs = get_students_for_teacher(user) if user_is_teacher(user) else None
        if user_is_admin(user):
            from accounts.models import User
            student_qs = User.objects.filter(
                is_active=True, role=User.Role.STUDENT,
            ).order_by('display_name')

        if request.method == 'POST':
            form = TeacherGoalForm(request.POST, student_queryset=student_qs)
            if form.is_valid():
                goal = form.save(commit=False)
                goal.created_by = user
                goal.visibility = Goal.Visibility.PUBLIC
                goal.save()
                messages.success(request, 'Goal created.')
                return redirect('growth:goal_detail', pk=goal.pk)
        else:
            form = TeacherGoalForm(student_queryset=student_qs)
        return render(request, 'growth/goals/goal_form.html', {
            'form': form,
            'title': 'New goal',
        })

    if not user_is_student(user):
        return redirect('growth:goal_list')

    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.student = user
            goal.created_by = user
            goal.save()
            messages.success(request, 'Goal created.')
            return redirect('growth:goal_detail', pk=goal.pk)
    else:
        form = GoalForm()
    return render(request, 'growth/goals/goal_form.html', {
        'form': form,
        'title': 'New goal',
    })


@login_required
def goal_detail(request, pk):
    goal = _get_goal_or_404(request.user, pk)
    feedback_list = goal.feedback.select_related('author').all()
    subgoals = goal.subgoals.all()

    from ..services.permissions import can_create_feedback
    context = {
        'goal': goal,
        'subgoals': subgoals,
        'feedback_list': feedback_list,
        'can_edit': can_edit_goal(request.user, goal),
        'can_delete': can_delete_goal(request.user, goal),
        'can_mark_achieved': can_mark_goal_achieved(request.user, goal),
        'can_give_feedback': can_create_feedback(request.user, goal),
        'can_manage_subgoals': can_manage_goal_subgoals(request.user, goal),
    }
    return render(request, 'growth/goals/goal_detail.html', context)


@login_required
def goal_edit(request, pk):
    goal = _get_goal_or_404(request.user, pk)
    if not can_edit_goal(request.user, goal):
        return HttpResponseForbidden('You cannot edit this goal.')

    if request.method == 'POST':
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Goal updated.')
            return redirect('growth:goal_detail', pk=goal.pk)
    else:
        form = GoalForm(instance=goal)
    return render(request, 'growth/goals/goal_form.html', {
        'form': form,
        'title': 'Edit goal',
    })


@login_required
def goal_delete(request, pk):
    goal = _get_goal_or_404(request.user, pk)
    if not can_delete_goal(request.user, goal):
        return HttpResponseForbidden('You cannot delete this goal.')

    if request.method == 'POST':
        goal.delete()
        messages.success(request, 'Goal deleted.')
        return redirect('growth:goal_list')
    return render(request, 'growth/goals/goal_confirm_delete.html', {'goal': goal})


@login_required
def goal_mark_achieved(request, pk):
    goal = _get_goal_or_404(request.user, pk)
    if not can_mark_goal_achieved(request.user, goal):
        return HttpResponseForbidden('You cannot mark this goal as achieved.')

    if request.method == 'POST':
        goal.status = Goal.Status.ACHIEVED
        goal.progress_percent = 100
        goal.achieved_at = timezone.now()
        goal.save()
        messages.success(request, 'Goal marked as achieved!')
        return redirect('growth:goal_detail', pk=goal.pk)
    return redirect('growth:goal_detail', pk=goal.pk)


# -- Subgoal views ---------------------------------------------------------

def _get_goal_for_subgoal_management(user, goal_pk):
    goal = get_object_or_404(Goal.objects.select_related('student', 'created_by'), pk=goal_pk)
    if not can_manage_goal_subgoals(user, goal):
        raise Http404
    return goal


@login_required
def subgoal_create(request, goal_pk):
    goal = _get_goal_for_subgoal_management(request.user, goal_pk)

    if request.method == 'POST':
        form = GoalSubgoalForm(request.POST)
        if form.is_valid():
            subgoal = form.save(commit=False)
            subgoal.goal = goal
            subgoal.created_by = request.user
            subgoal.save()
            messages.success(request, 'Subgoal added.')
            return redirect('growth:goal_detail', pk=goal.pk)
    else:
        form = GoalSubgoalForm()
    return render(request, 'growth/goals/subgoal_form.html', {
        'form': form,
        'goal': goal,
        'title': 'New subgoal',
    })


@login_required
def subgoal_edit(request, goal_pk, subgoal_pk):
    goal = _get_goal_for_subgoal_management(request.user, goal_pk)
    subgoal = get_object_or_404(GoalSubgoal, pk=subgoal_pk, goal=goal)
    if not can_edit_subgoal(request.user, subgoal):
        return HttpResponseForbidden('You cannot edit this subgoal.')

    if request.method == 'POST':
        form = GoalSubgoalForm(request.POST, instance=subgoal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subgoal updated.')
            return redirect('growth:goal_detail', pk=goal.pk)
    else:
        form = GoalSubgoalForm(instance=subgoal)
    return render(request, 'growth/goals/subgoal_form.html', {
        'form': form,
        'goal': goal,
        'title': 'Edit subgoal',
    })


@login_required
def subgoal_delete(request, goal_pk, subgoal_pk):
    goal = _get_goal_for_subgoal_management(request.user, goal_pk)
    subgoal = get_object_or_404(GoalSubgoal, pk=subgoal_pk, goal=goal)
    if not can_delete_subgoal(request.user, subgoal):
        return HttpResponseForbidden('You cannot delete this subgoal.')

    if request.method == 'POST':
        subgoal.delete()
        messages.success(request, 'Subgoal deleted.')
        return redirect('growth:goal_detail', pk=goal.pk)
    return render(request, 'growth/goals/subgoal_confirm_delete.html', {
        'subgoal': subgoal,
        'goal': goal,
    })


@login_required
def subgoal_toggle(request, goal_pk, subgoal_pk):
    goal = _get_goal_for_subgoal_management(request.user, goal_pk)
    subgoal = get_object_or_404(GoalSubgoal, pk=subgoal_pk, goal=goal)
    if not can_toggle_subgoal(request.user, subgoal):
        return HttpResponseForbidden('You cannot toggle this subgoal.')

    if request.method == 'POST':
        if subgoal.status == GoalSubgoal.Status.PENDING:
            subgoal.status = GoalSubgoal.Status.DONE
            subgoal.completed_at = timezone.now()
        else:
            subgoal.status = GoalSubgoal.Status.PENDING
            subgoal.completed_at = None
        subgoal.save()

    return redirect('growth:goal_detail', pk=goal.pk)
