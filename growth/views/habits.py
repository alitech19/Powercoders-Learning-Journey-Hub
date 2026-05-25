from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..forms import HabitForm
from ..models import Habit, HabitLog
from ..selectors import get_visible_habits_for_user
from ..services.habits import (
    get_current_weekly_streak,
    get_done_count_for_week,
    get_week_start,
)
from ..services.permissions import (
    can_complete_habit,
    can_delete_habit,
    can_edit_habit,
    can_log_habit,
    can_reactivate_habit,
    can_view_habit,
)
from tracker.permissions import user_is_student


def _get_habit_or_404(user, pk):
    habit = get_object_or_404(
        Habit.objects.select_related('student'), pk=pk,
    )
    if not can_view_habit(user, habit):
        raise Http404
    return habit


@login_required
def habit_list(request):
    habits = get_visible_habits_for_user(request.user)
    today = timezone.localdate()
    is_student = user_is_student(request.user)
    week_start = get_week_start(today)

    active_habits = []
    for h in habits.filter(status=Habit.Status.ACTIVE):
        today_log = h.logs.filter(date=today).first()
        done_this_week = get_done_count_for_week(h, week_start)
        streak = get_current_weekly_streak(h, today)
        active_habits.append({
            'habit': h,
            'today_log': today_log,
            'done_this_week': done_this_week,
            'streak': streak,
            'can_log': is_student and h.student_id == request.user.pk,
        })

    completed_habits_qs = habits.filter(status=Habit.Status.COMPLETED)
    completed_habits = []
    for h in completed_habits_qs:
        completed_habits.append({
            'habit': h,
            'can_reactivate': is_student and h.student_id == request.user.pk,
            'can_delete': is_student and h.student_id == request.user.pk,
        })

    return render(request, 'growth/habits/habit_list.html', {
        'active_habits': active_habits,
        'completed_habits': completed_habits,
        'is_student': is_student,
    })


@login_required
def habit_create(request):
    if not user_is_student(request.user):
        return redirect('growth:habit_list')

    if request.method == 'POST':
        form = HabitForm(request.POST)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.student = request.user
            habit.save()
            messages.success(request, 'Habit created.')
            return redirect('growth:habit_list')
    else:
        form = HabitForm()
    return render(request, 'growth/habits/habit_form.html', {
        'form': form,
        'title': 'New habit',
    })


@login_required
def habit_edit(request, pk):
    habit = _get_habit_or_404(request.user, pk)
    if not can_edit_habit(request.user, habit):
        return HttpResponseForbidden('You cannot edit this habit.')

    if request.method == 'POST':
        form = HabitForm(request.POST, instance=habit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Habit updated.')
            return redirect('growth:habit_list')
    else:
        form = HabitForm(instance=habit)
    return render(request, 'growth/habits/habit_form.html', {
        'form': form,
        'title': 'Edit habit',
    })


@login_required
def habit_delete(request, pk):
    habit = _get_habit_or_404(request.user, pk)
    if not can_delete_habit(request.user, habit):
        return HttpResponseForbidden('You cannot delete this habit.')

    if request.method == 'POST':
        habit.delete()
        messages.success(request, 'Habit deleted.')
        return redirect('growth:habit_list')

    return render(request, 'growth/habits/habit_confirm_delete.html', {
        'habit': habit,
    })


@login_required
def habit_mark_completed(request, pk):
    habit = _get_habit_or_404(request.user, pk)
    if not can_complete_habit(request.user, habit):
        return HttpResponseForbidden('You cannot complete this habit.')

    today = timezone.localdate()
    streak = get_current_weekly_streak(habit, today)

    if request.method == 'POST':
        habit.completed_weekly_streak = streak
        habit.status = Habit.Status.COMPLETED
        habit.completed_at = timezone.now()
        habit.save()
        messages.success(request, 'Habit marked as completed.')
        return redirect('growth:habit_list')

    return render(request, 'growth/habits/habit_confirm_complete.html', {
        'habit': habit,
        'streak': streak,
    })


@login_required
def habit_reactivate(request, pk):
    habit = _get_habit_or_404(request.user, pk)
    if not can_reactivate_habit(request.user, habit):
        return HttpResponseForbidden('You cannot reactivate this habit.')

    habit.status = Habit.Status.ACTIVE
    habit.completed_at = None
    habit.completed_weekly_streak = 0
    habit.save()
    messages.success(request, 'Habit reactivated.')
    return redirect('growth:habit_list')


@login_required
def habit_log_done(request, pk):
    if request.method != 'POST':
        return redirect('growth:habit_list')

    habit = _get_habit_or_404(request.user, pk)
    if not can_log_habit(request.user, habit):
        return HttpResponseForbidden('You cannot log this habit.')

    HabitLog.objects.update_or_create(
        habit=habit,
        date=timezone.localdate(),
        defaults={'status': HabitLog.Status.DONE},
    )
    return redirect('growth:habit_list')


@login_required
def habit_log_not_done(request, pk):
    if request.method != 'POST':
        return redirect('growth:habit_list')

    habit = _get_habit_or_404(request.user, pk)
    if not can_log_habit(request.user, habit):
        return HttpResponseForbidden('You cannot log this habit.')

    HabitLog.objects.update_or_create(
        habit=habit,
        date=timezone.localdate(),
        defaults={'status': HabitLog.Status.NOT_DONE},
    )
    return redirect('growth:habit_list')
