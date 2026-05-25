from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..forms import GoalForm
from ..models import Goal
from ..selectors import get_visible_goals_for_user
from ..services.permissions import (
    can_delete_goal,
    can_edit_goal,
    can_mark_goal_achieved,
    can_view_goal,
)
from tracker.permissions import user_is_student


def _get_goal_or_404(user, pk):
    goal = get_object_or_404(Goal.objects.select_related('student'), pk=pk)
    if not can_view_goal(user, goal):
        raise Http404
    return goal


@login_required
def goal_list(request):
    goals = get_visible_goals_for_user(request.user)
    context = {
        'goals': goals,
        'is_student': user_is_student(request.user),
    }
    return render(request, 'growth/goals/goal_list.html', context)


@login_required
def goal_create(request):
    if not user_is_student(request.user):
        return redirect('growth:goal_list')

    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.student = request.user
            goal.save()
            messages.success(request, 'Goal created.')
            return redirect('growth:goal_detail', pk=goal.pk)
    else:
        form = GoalForm()
    return render(request, 'growth/goals/goal_form.html', {
        'form': form,
        'title': 'New SMART goal',
    })


@login_required
def goal_detail(request, pk):
    goal = _get_goal_or_404(request.user, pk)
    feedback_list = goal.feedback.select_related('author').all()

    from ..services.permissions import can_create_feedback
    context = {
        'goal': goal,
        'feedback_list': feedback_list,
        'can_edit': can_edit_goal(request.user, goal),
        'can_delete': can_delete_goal(request.user, goal),
        'can_mark_achieved': can_mark_goal_achieved(request.user, goal),
        'can_give_feedback': can_create_feedback(request.user, goal),
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
        goal.achieved_at = timezone.now()
        goal.save()
        messages.success(request, 'Goal marked as achieved!')
        return redirect('growth:goal_detail', pk=goal.pk)
    return redirect('growth:goal_detail', pk=goal.pk)
