"""Dashboard aggregations — read-only summaries from other apps."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Prefetch, Q
from django.utils import timezone

from cohorts.permissions import user_is_student
from goals.models import GoalEnrollment
from goals.permissions import get_visible_goals_for_user
from group_space.models import Post
from habits.models import Habit, HabitLog
from journal.models import JournalEntry
from reflections.constants import TAG_WEEKLY
from reflections.models import Reflection
from resources.models import ResourceContainer, ResourceItem
from tasks.models import Task, TaskEnrollment
from tasks.permissions import (
    can_change_status,
    can_view_task_content,
    can_view_task_metadata,
    get_enrollment_for_user,
    get_visible_tasks_for_user,
)
from workflows.models import Workflow, WorkflowEnrollment
from workflows.permissions import get_visible_workflows_for_user

User = get_user_model()


def tasks_queryset():
    return Task.objects.select_related(
        'author',
        'created_by',
        'assignee_user',
        'assignee_group',
        'assignee_group__cohort',
        'assignee_cohort',
    ).prefetch_related(
        'subtasks',
        Prefetch(
            'enrollments',
            queryset=TaskEnrollment.objects.select_related('student', 'student__group'),
        ),
    )


def this_week_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def week_start_datetime():
    return timezone.make_aware(datetime.combine(this_week_monday(), time.min))


def user_has_weekly_reflection_this_week(user) -> bool:
    return Reflection.objects.filter(
        author=user,
        tags__contains=[TAG_WEEKLY],
        final_reflection_at__gte=week_start_datetime(),
    ).exists()


def students_missing_weekly_reflection(students):
    week_start = week_start_datetime()
    submitted_ids = set(
        Reflection.objects.filter(
            author__in=students,
            tags__contains=[TAG_WEEKLY],
            final_reflection_at__gte=week_start,
        ).values_list('author_id', flat=True)
    )
    return [student for student in students if student.pk not in submitted_ids]


def _effective_status(task, enrollment):
    if task.is_group_shared:
        return task.status
    return enrollment.status if enrollment else task.status


def build_task_rows(tasks, *, user, filtered_student=None):
    rows = []
    for task in tasks:
        enrollment = None
        if not task.is_group_shared:
            if user_is_student(user):
                enrollment = get_enrollment_for_user(user, task)
            elif filtered_student:
                enrollment = task.enrollments.filter(student=filtered_student).first()
        rows.append(
            {
                'task': task,
                'enrollment': enrollment,
                'can_view_content': can_view_task_content(user, task),
                'can_view_metadata': can_view_task_metadata(user, task),
                'can_edit_status': can_change_status(user, task, enrollment),
                'display_status': _effective_status(task, enrollment),
            }
        )
    return rows


def tasks_by_status_for_student(user, tasks):
    counts: dict[str, int] = {}
    for task in tasks:
        enrollment = get_enrollment_for_user(user, task)
        status = _effective_status(task, enrollment)
        counts[status] = counts.get(status, 0) + 1
    return counts


def tasks_for_kind(user, kind):
    visible_pks = get_visible_tasks_for_user(user).values_list('pk', flat=True)
    tasks = tasks_queryset().filter(pk__in=visible_pks)
    return [task for task in tasks if task.list_kind == kind]


def public_tasks_queryset(user):
    visible = get_visible_tasks_for_user(user)
    return visible.filter(
        Q(visibility=Task.Visibility.SHARED)
        | Q(
            assignee_type=Task.AssigneeType.GROUP,
            progress_mode=Task.ProgressMode.SHARED,
        )
    ).distinct()


def private_student_metadata_queryset(user):
    visible = get_visible_tasks_for_user(user)
    return visible.filter(
        visibility=Task.Visibility.PRIVATE,
        author__isnull=False,
    ).distinct()


def student_goal_stats(user):
    visible = get_visible_goals_for_user(user)
    enrollments = GoalEnrollment.objects.filter(
        student=user,
        goal__in=visible,
    )
    return {
        'goals_total': visible.count(),
        'goals_in_progress': enrollments.filter(
            status=GoalEnrollment.Status.IN_PROGRESS,
        ).count(),
        'last_goal_updated': visible.order_by('-updated_at')
        .values_list('updated_at', flat=True)
        .first(),
    }


def student_habit_stats(user):
    active = Habit.objects.filter(author=user, status=Habit.Status.ACTIVE)
    logs_this_week = HabitLog.objects.filter(
        habit__author=user,
        date__gte=this_week_monday(),
        status=HabitLog.Status.DONE,
    ).count()
    return {
        'habits_active': active.count(),
        'habit_logs_week': logs_this_week,
    }


def student_workflow_stats(user):
    visible = get_visible_workflows_for_user(user)
    enrolled = WorkflowEnrollment.objects.filter(
        student=user,
        workflow__in=visible,
    ).select_related('workflow')
    in_progress = 0
    for enrollment in enrolled:
        if enrollment.progress_pct() < 100:
            in_progress += 1
    return {
        'workflows_visible': visible.count(),
        'workflows_enrolled': enrolled.count(),
        'workflows_in_progress': in_progress,
    }


def student_group_stats(user):
    if not user.group_id:
        return {'group_posts_week': 0, 'has_group': False}
    week_ago = timezone.now() - timedelta(days=7)
    posts_week = Post.objects.filter(
        group_space__group_id=user.group_id,
        created_at__gte=week_ago,
    ).count()
    return {'group_posts_week': posts_week, 'has_group': True}


def student_resource_stats(user):
    personal_items = ResourceItem.objects.filter(
        container__container_type=ResourceContainer.ContainerType.PERSONAL,
        container__owner=user,
    ).count()
    group_items = 0
    if user.group_id:
        group_items = ResourceItem.objects.filter(
            container__container_type=ResourceContainer.ContainerType.GROUP,
            container__group_id=user.group_id,
        ).count()
    return {
        'resource_personal_items': personal_items,
        'resource_group_items': group_items,
    }


def admin_extra_stats():
    one_week_ago = timezone.now() - timedelta(days=7)
    return {
        'habits_active': Habit.objects.filter(status=Habit.Status.ACTIVE).count(),
        'workflows_total': Workflow.objects.count(),
        'group_posts_week': Post.objects.filter(created_at__gte=one_week_ago).count(),
        'resource_items': ResourceItem.objects.count(),
    }
