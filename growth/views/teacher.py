from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from accounts.models import User
from tracker.permissions import user_is_admin, user_is_teacher

from ..models import DailyJournalEntry, Goal, Habit, WeeklyReflection
from ..selectors import get_students_for_teacher
from ..services.dashboard import get_growth_summary_for_student
from ..services.habits import (
    build_week_table,
    get_current_weekly_streak,
    get_done_count_for_week,
    get_week_start,
)
from ..services.permissions import can_create_feedback


@login_required
def teacher_dashboard(request):
    user = request.user
    if not (user_is_teacher(user) or user_is_admin(user)):
        raise Http404

    if user_is_admin(user):
        students = User.objects.filter(
            is_active=True, role=User.Role.STUDENT,
        ).order_by('display_name')
    else:
        students = get_students_for_teacher(user)

    rows = []
    for student in students:
        summary = get_growth_summary_for_student(student)
        rows.append({'student': student, **summary})

    return render(request, 'growth/teacher/dashboard.html', {'rows': rows})


@login_required
def student_growth_detail(request, student_id):
    user = request.user
    if not (user_is_teacher(user) or user_is_admin(user)):
        raise Http404

    student = get_object_or_404(User, pk=student_id, role=User.Role.STUDENT)

    if user_is_teacher(user):
        allowed_ids = get_students_for_teacher(user).values_list('pk', flat=True)
        if student.pk not in allowed_ids:
            raise Http404

    today = timezone.now().date()
    week_start = get_week_start(today)

    goals = Goal.objects.filter(
        student=student, visibility=Goal.Visibility.PUBLIC,
    ).order_by('-updated_at')

    reflections = WeeklyReflection.objects.filter(
        student=student,
    ).order_by('-week_start')

    journal_entries = DailyJournalEntry.objects.filter(
        student=student,
    ).order_by('-entry_date')

    active_habits = Habit.objects.filter(
        student=student, status=Habit.Status.ACTIVE,
    ).order_by('-updated_at')

    completed_habits = Habit.objects.filter(
        student=student, status=Habit.Status.COMPLETED,
    ).order_by('-completed_at')

    goal_fb = [
        {'item': g, 'can_give_feedback': can_create_feedback(user, g)}
        for g in goals
    ]
    refl_fb = [
        {'item': r, 'can_give_feedback': can_create_feedback(user, r)}
        for r in reflections
    ]
    journal_fb = [
        {'item': j, 'can_give_feedback': can_create_feedback(user, j)}
        for j in journal_entries
    ]

    habit_rows = []
    for h in list(active_habits) + list(completed_habits):
        done_this_week = get_done_count_for_week(h, week_start)
        streak = get_current_weekly_streak(h, today)
        week_table = build_week_table(h, today)
        habit_rows.append({
            'item': h,
            'can_give_feedback': can_create_feedback(user, h),
            'done_this_week': done_this_week,
            'streak': streak,
            'week_table': week_table,
        })

    return render(request, 'growth/teacher/student_growth_detail.html', {
        'student': student,
        'goal_rows': goal_fb,
        'reflection_rows': refl_fb,
        'journal_rows': journal_fb,
        'habit_rows': habit_rows,
    })
