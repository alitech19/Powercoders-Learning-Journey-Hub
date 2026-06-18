from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from cohorts.permissions import (
    get_teacher_accessible_students,
    user_is_admin,
    user_is_student,
    user_is_teacher,
)

from config.input_limits import SEARCH_QUERY_MAX_LENGTH
from feedback.services import build_section_context

from .forms import HabitForm
from .models import Habit, HabitLog
from .permissions import (
    can_complete_habit,
    can_create_habits,
    can_delete_habit,
    can_edit_habit,
    can_log_habit,
    can_reactivate_habit,
    can_view_habit,
    filter_habits_queryset,
    get_visible_habits_for_user,
    order_habits_newest_first,
)
from .services import (
    build_habit_row,
    get_current_weekly_streak,
    get_week_start,
    student_habit_stats,
)


def _get_habit_or_404(user, pk):
    habit = get_object_or_404(
        Habit.objects.select_related('author', 'author__group').prefetch_related('logs'),
        pk=pk,
    )
    if not can_view_habit(user, habit):
        raise PermissionDenied
    return habit


def _redirect_after_action(request, habit, *, fallback='detail'):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    if fallback == 'list':
        return redirect('habits:list')
    return redirect('habits:detail', pk=habit.pk)


def _list_query_params(request):
    return {
        'search_query': request.GET.get('q', '').strip()[:SEARCH_QUERY_MAX_LENGTH],
        'student_filter': request.GET.get('student', ''),
    }


def _build_habit_lists(user, habits_qs, today, week_start):
    is_owner_student = user_is_student(user)
    active_rows = []
    for habit in habits_qs.filter(status=Habit.Status.ACTIVE):
        can_log = is_owner_student and habit.author_id == user.pk
        active_rows.append(build_habit_row(
            habit, today=today, week_start=week_start, can_log=can_log,
        ))
    completed_rows = []
    for habit in habits_qs.filter(status=Habit.Status.COMPLETED):
        completed_rows.append({
            'habit': habit,
            'can_reactivate': is_owner_student and habit.author_id == user.pk,
            'can_delete': is_owner_student and habit.author_id == user.pk,
        })
    return active_rows, completed_rows


@login_required
def habit_list(request):
    user = request.user
    params = _list_query_params(request)
    today = timezone.localdate()
    week_start = get_week_start(today)

    qs = get_visible_habits_for_user(user).prefetch_related('logs')
    qs = filter_habits_queryset(
        qs,
        search=params['search_query'] or None,
        student_id=params['student_filter'] if params['student_filter'].isdigit() else None,
    )
    qs = order_habits_newest_first(qs)

    active_rows, completed_rows = _build_habit_lists(user, qs, today, week_start)

    if user_is_student(user):
        all_own = get_visible_habits_for_user(user)
        stats = student_habit_stats(all_own, today)
        context = {
            'view_as': 'student',
            'can_create': can_create_habits(user),
            'students': None,
            **stats,
        }
    else:
        if user_is_admin(user):
            students = User.objects.filter(
                role=User.Role.STUDENT, is_active=True,
            ).order_by('display_name')
        else:
            students = get_teacher_accessible_students(user)
        context = {
            'view_as': 'admin' if user_is_admin(user) else 'teacher',
            'students': students,
            'can_create': False,
        }

    status_filter = request.GET.get('status', 'active')
    if status_filter not in ('active', 'finished'):
        status_filter = 'active'

    context.update({
        'active_rows': active_rows,
        'completed_rows': completed_rows,
        'search_query': params['search_query'],
        'student_filter': params['student_filter'],
        'status_filter': status_filter,
        'today': today,
    })
    return render(request, 'habits/habit_list.html', context)


@login_required
def habit_create(request):
    if not can_create_habits(request.user):
        return redirect('habits:list')

    if request.method == 'POST':
        form = HabitForm(request.POST)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.author = request.user
            habit.save()
            messages.success(request, 'Habit created.')
            return redirect('habits:detail', pk=habit.pk)
    else:
        form = HabitForm()

    return render(request, 'habits/habit_form.html', {
        'form': form,
        'action': 'create',
    })


@login_required
def habit_detail(request, pk):
    habit = _get_habit_or_404(request.user, pk)
    user = request.user
    today = timezone.localdate()
    week_start = get_week_start(today)
    row = build_habit_row(
        habit,
        today=today,
        week_start=week_start,
        can_log=can_log_habit(user, habit),
    )
    is_staff_view = user.pk != habit.author_id and (
        user_is_teacher(user) or user_is_admin(user)
    )
    ctx = {
        'habit': habit,
        'row': row,
        'can_edit': can_edit_habit(user, habit),
        'can_delete': can_delete_habit(user, habit),
        'can_complete': can_complete_habit(user, habit),
        'can_reactivate': can_reactivate_habit(user, habit),
        'can_log': can_log_habit(user, habit),
        'is_staff_view': is_staff_view,
        'list_url': reverse('habits:list'),
    }
    feedback_ctx = build_section_context(target=habit, viewer=user)
    if feedback_ctx:
        ctx.update(feedback_ctx)
        ctx['show_feedback'] = True
    else:
        ctx['show_feedback'] = False
    return render(request, 'habits/habit_detail.html', ctx)


@login_required
def habit_edit(request, pk):
    habit = _get_habit_or_404(request.user, pk)
    if not can_edit_habit(request.user, habit):
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = HabitForm(request.POST, instance=habit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Habit updated.')
            return redirect('habits:detail', pk=habit.pk)
    else:
        form = HabitForm(instance=habit)

    return render(request, 'habits/habit_form.html', {
        'form': form,
        'action': 'edit',
        'habit': habit,
    })


@login_required
def habit_delete(request, pk):
    habit = _get_habit_or_404(request.user, pk)
    if not can_delete_habit(request.user, habit):
        return HttpResponseForbidden()
    if request.method == 'POST':
        habit.delete()
        messages.success(request, 'Habit deleted.')
        return redirect('habits:list')
    return render(request, 'habits/habit_confirm_delete.html', {'habit': habit})


@login_required
def habit_complete(request, pk):
    habit = _get_habit_or_404(request.user, pk)
    if not can_complete_habit(request.user, habit):
        return HttpResponseForbidden()

    today = timezone.localdate()
    streak = get_current_weekly_streak(habit, today)

    if request.method == 'POST':
        habit.completed_weekly_streak = streak
        habit.status = Habit.Status.COMPLETED
        habit.completed_at = timezone.now()
        habit.save()
        messages.success(request, 'Habit marked as completed.')
        return redirect('habits:list')

    return render(request, 'habits/habit_confirm_complete.html', {
        'habit': habit,
        'streak': streak,
    })


@login_required
@require_POST
def habit_reactivate(request, pk):
    habit = _get_habit_or_404(request.user, pk)
    if not can_reactivate_habit(request.user, habit):
        return HttpResponseForbidden()
    habit.status = Habit.Status.ACTIVE
    habit.completed_at = None
    habit.completed_weekly_streak = 0
    habit.save()
    messages.success(request, 'Habit reactivated.')
    return _redirect_after_action(request, habit, fallback='list')


@login_required
@require_POST
def habit_log_done(request, pk):
    habit = _get_habit_or_404(request.user, pk)
    if not can_log_habit(request.user, habit):
        return HttpResponseForbidden()
    HabitLog.objects.update_or_create(
        habit=habit,
        date=timezone.localdate(),
        defaults={'status': HabitLog.Status.DONE},
    )
    return _redirect_after_action(request, habit)


@login_required
@require_POST
def habit_log_not_done(request, pk):
    habit = _get_habit_or_404(request.user, pk)
    if not can_log_habit(request.user, habit):
        return HttpResponseForbidden()
    HabitLog.objects.update_or_create(
        habit=habit,
        date=timezone.localdate(),
        defaults={'status': HabitLog.Status.NOT_DONE},
    )
    return _redirect_after_action(request, habit)
