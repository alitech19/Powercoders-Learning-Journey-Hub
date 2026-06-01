"""Student progress stats for teacher/admin oversight views."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Max, Q
from django.utils import timezone

from dashboard.services import students_missing_weekly_reflection
from goals.models import GoalEnrollment
from group_space.models import Post
from habits.models import Habit, HabitLog
from journal.models import JournalEntry
from journal.services import writing_streak
from reflections.models import Reflection
from resources.models import ResourceItem
from tasks.models import Task, TaskEnrollment
from workflows.models import WorkflowEnrollment

User = get_user_model()


def _ratio_cell(done, total):
    if total <= 0:
        return '—'
    return f'{done}/{total}'


def _task_stats_by_student(student_ids):
    totals = defaultdict(lambda: {'total': 0, 'done': 0})
    rows = (
        TaskEnrollment.objects.filter(student_id__in=student_ids)
        .values('student_id')
        .annotate(
            total=Count('pk'),
            done=Count('pk', filter=Q(status=Task.Status.DONE)),
        )
    )
    for row in rows:
        totals[row['student_id']] = {'total': row['total'], 'done': row['done']}
    return totals


def _goal_stats_by_student(student_ids):
    totals = defaultdict(lambda: {'total': 0, 'completed': 0})
    rows = (
        GoalEnrollment.objects.filter(student_id__in=student_ids)
        .values('student_id')
        .annotate(
            total=Count('pk'),
            completed=Count(
                'pk',
                filter=Q(status=GoalEnrollment.Status.COMPLETED),
            ),
        )
    )
    for row in rows:
        totals[row['student_id']] = {
            'total': row['total'],
            'completed': row['completed'],
        }
    return totals


def _workflow_stats_by_student(student_ids):
    totals = defaultdict(lambda: {'total': 0, 'completed': 0})
    enrollments = (
        WorkflowEnrollment.objects.filter(student_id__in=student_ids)
        .select_related('workflow')
        .prefetch_related('workflow__steps')
    )
    for enrollment in enrollments:
        sid = enrollment.student_id
        totals[sid]['total'] += 1
        if enrollment.progress_pct() >= 100:
            totals[sid]['completed'] += 1
    return totals


def _journal_stats_by_student(student_ids):
    totals = defaultdict(lambda: {'total': 0, 'last': None})
    rows = (
        JournalEntry.objects.filter(author_id__in=student_ids)
        .values('author_id')
        .annotate(total=Count('pk'), last=Max('entry_date'))
    )
    for row in rows:
        totals[row['author_id']] = {'total': row['total'], 'last': row['last']}
    return totals


def _reflection_stats_by_student(student_ids):
    totals = defaultdict(lambda: {'total': 0, 'last': None})
    rows = (
        Reflection.objects.filter(author_id__in=student_ids)
        .values('author_id')
        .annotate(
            total=Count('pk'),
            last=Max('final_reflection_at'),
        )
    )
    for row in rows:
        totals[row['author_id']] = {'total': row['total'], 'last': row['last']}
    return totals


def _habit_stats_by_student(student_ids):
    totals = defaultdict(lambda: {'active': 0, 'logs_week': 0})
    active_rows = (
        Habit.objects.filter(author_id__in=student_ids, status=Habit.Status.ACTIVE)
        .values('author_id')
        .annotate(active=Count('pk'))
    )
    for row in active_rows:
        totals[row['author_id']]['active'] = row['active']

    week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
    log_rows = (
        HabitLog.objects.filter(
            habit__author_id__in=student_ids,
            date__gte=week_start,
        )
        .values('habit__author_id')
        .annotate(logs=Count('pk'))
    )
    for row in log_rows:
        totals[row['habit__author_id']]['logs_week'] = row['logs']
    return totals


def _group_post_stats_by_student(student_ids):
    totals = defaultdict(int)
    week_ago = timezone.now() - timedelta(days=7)
    rows = (
        Post.objects.filter(author_id__in=student_ids, created_at__gte=week_ago)
        .values('author_id')
        .annotate(total=Count('pk'))
    )
    for row in rows:
        totals[row['author_id']] = row['total']
    return totals


def _resource_stats_by_student(student_ids):
    totals = defaultdict(int)
    rows = (
        ResourceItem.objects.filter(created_by_id__in=student_ids)
        .values('created_by_id')
        .annotate(total=Count('pk'))
    )
    for row in rows:
        totals[row['created_by_id']] = row['total']
    return totals


def enrich_students_for_progress(students):
    """Attach nav-order learning metrics on each student (see config.nav.NAV_REGISTRY)."""
    student_list = list(students)
    if not student_list:
        return student_list

    ids = [s.pk for s in student_list]
    workflow_stats = _workflow_stats_by_student(ids)
    goal_stats = _goal_stats_by_student(ids)
    task_stats = _task_stats_by_student(ids)
    reflection_stats = _reflection_stats_by_student(ids)
    journal_stats = _journal_stats_by_student(ids)
    habit_stats = _habit_stats_by_student(ids)
    group_stats = _group_post_stats_by_student(ids)
    resource_stats = _resource_stats_by_student(ids)

    for student in student_list:
        ws = workflow_stats[student.pk]
        gs = goal_stats[student.pk]
        ts = task_stats[student.pk]
        rs = reflection_stats[student.pk]
        js = journal_stats[student.pk]
        hs = habit_stats[student.pk]

        student.workflow_total = ws['total']
        student.workflow_completed = ws['completed']
        student.workflow_label = _ratio_cell(ws['completed'], ws['total'])

        student.goal_total = gs['total']
        student.goal_completed = gs['completed']
        student.goal_label = _ratio_cell(gs['completed'], gs['total'])

        student.task_total = ts['total']
        student.task_done = ts['done']
        student.task_label = _ratio_cell(ts['done'], ts['total'])

        student.reflection_total = rs['total']
        student.last_reflection = rs['last']

        student.journal_total = js['total']
        student.last_journal = js['last']

        student.habits_active = hs['active']
        student.habit_logs_week = hs['logs_week']

        student.group_posts_week = group_stats[student.pk]
        student.resources_count = resource_stats[student.pk]

    return student_list


def build_student_progress_rows(students_qs, *, missing_filter=False):
    """Return paginator-ready rows: {student, streak, missing_reflection}."""
    students = enrich_students_for_progress(
        students_qs.select_related('group', 'cohort').order_by('group__name', 'display_name')
    )
    missing_set = {s.pk for s in students_missing_weekly_reflection(students)}
    rows = [
        {
            'student': student,
            'streak': writing_streak(student),
            'missing_reflection': student.pk in missing_set,
        }
        for student in students
    ]
    if missing_filter:
        rows = [row for row in rows if row['missing_reflection']]
    return rows


def teacher_can_view_student(viewer, student):
    if viewer.role == User.Role.ADMIN:
        return True
    if viewer.role != User.Role.TEACHER:
        return False
    if not student.group_id:
        return False
    from cohorts.permissions import get_teacher_group_ids

    return student.group_id in get_teacher_group_ids(viewer)


def goal_enrollments_for_student(student, *, limit=15):
    from goals.models import Goal

    return (
        GoalEnrollment.objects.filter(
            student=student,
            goal__visibility=Goal.Visibility.SHARED,
        )
        .select_related('goal')
        .prefetch_related('goal__milestones')
        .order_by('-goal__updated_at')[:limit]
    )


def workflow_enrollments_for_student(student, *, limit=15):
    return (
        WorkflowEnrollment.objects.filter(student=student)
        .select_related('workflow')
        .prefetch_related('workflow__steps')
        .order_by('-enrolled_at')[:limit]
    )


def shared_habits_for_student(student, *, limit=15):
    return (
        Habit.objects.filter(author=student, visibility=Habit.Visibility.SHARED)
        .order_by('-updated_at')[:limit]
    )
