"""
Snapshot builders — collect structured JSON into snapshot_meta.

Snapshots are rendered at display time from snapshot_meta (JSONField),
so stored posts stay stable when templates change.
snapshot_html is left empty for new shares; legacy posts may still have HTML.
"""

from django.utils import timezone

from goals.models import Goal
from goals.permissions import get_enrollment_for_user as get_goal_enrollment
from habits.models import Habit, HabitLog
from journal.models import JournalEntry
from tasks.models import Task
from tasks.permissions import get_enrollment_for_user as get_task_enrollment

from config.module_access import is_module_enabled
from config.modules import SNAPSHOT_KIND_TO_SLUG

from .constants import SNAPSHOT_KINDS
from .models import Post


def _goal_milestones(enrollment):
    if not enrollment:
        return []
    completed = enrollment.completed_milestone_ids()
    return [
        {'title': milestone.title, 'completed': milestone.pk in completed}
        for milestone in enrollment.goal.milestones.all()
    ]


def _task_subtasks(enrollment):
    if not enrollment:
        return []
    completed = enrollment.completed_subtask_ids()
    return [
        {'title': subtask.title, 'completed': subtask.pk in completed}
        for subtask in enrollment.task.subtasks.all().order_by('order', 'pk')
    ]


def build_journal_snapshot(entry):
    meta = {
        'kind': Post.SnapshotKind.JOURNAL,
        'kind_label': 'Journal entry',
        'title': entry.title,
        'entry_date': entry.entry_date.isoformat(),
        'mood': entry.mood,
        'mood_emoji': entry.mood_emoji,
        'word_count': entry.word_count,
        'tags': entry.get_tags_list(),
        'content_preview': (entry.content or '')[:300],
    }
    return Post.SnapshotKind.JOURNAL, '', meta


def build_habit_snapshot(habit, user):
    from habits.services import build_habit_row, build_week_table, get_week_start

    today = timezone.localdate()
    week_start = get_week_start(today)
    row = build_habit_row(habit, today=today, week_start=week_start, can_log=False)
    week = build_week_table(habit, today)

    meta = {
        'kind': Post.SnapshotKind.HABIT,
        'kind_label': 'Habit',
        'title': habit.title,
        'status': habit.status,
        'description': habit.description or '',
        'target_days_per_week': habit.target_days_per_week,
        'target_minutes': habit.target_minutes,
        'done_this_week': row['done_this_week'],
        'streak': row['streak'],
        'week_table': [
            {
                'weekday': day['weekday'],
                'done': bool(day['log'] and day['log'].status == HabitLog.Status.DONE),
                'is_today': day['is_today'],
            }
            for day in week
        ],
    }
    return Post.SnapshotKind.HABIT, '', meta


def build_goal_snapshot(goal, enrollment):
    milestones = _goal_milestones(enrollment)
    done = sum(1 for milestone in milestones if milestone['completed'])
    total = len(milestones)
    progress = enrollment.progress if enrollment else (round(done / total * 100) if total else 0)

    meta = {
        'kind': Post.SnapshotKind.GOAL,
        'kind_label': 'Goal',
        'title': goal.title,
        'category': goal.get_category_display(),
        'status_value': enrollment.status if enrollment else '',
        'status_label': enrollment.get_status_display() if enrollment else '',
        'description': goal.description or '',
        'target_date': goal.target_date.isoformat() if goal.target_date else None,
        'milestones': milestones,
        'milestones_done': done,
        'milestones_total': total,
        'progress': progress,
    }
    return Post.SnapshotKind.GOAL, '', meta


def build_task_snapshot(task, enrollment):
    subtasks = _task_subtasks(enrollment)
    status = enrollment.status if enrollment else task.status

    meta = {
        'kind': Post.SnapshotKind.TASK,
        'kind_label': 'Task',
        'title': task.title,
        'priority': task.priority,
        'priority_label': task.get_priority_display(),
        'status': status,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'description': task.description or '',
        'subtasks': subtasks,
        'subtasks_done': sum(1 for item in subtasks if item['completed']),
        'subtasks_total': len(subtasks),
    }
    return Post.SnapshotKind.TASK, '', meta


def get_shareable_journal_entries(user):
    return JournalEntry.objects.filter(
        author=user,
        visibility=JournalEntry.Visibility.SHARED,
    ).order_by('-entry_date', '-created_at')


def get_shareable_habits(user):
    return Habit.objects.filter(
        author=user,
        visibility=Habit.Visibility.SHARED,
    ).order_by('-updated_at')


def get_shareable_goals(user):
    return Goal.objects.filter(
        enrollments__student=user,
        visibility=Goal.Visibility.SHARED,
    ).distinct().order_by('-updated_at')


def get_shareable_tasks(user):
    return Task.objects.filter(
        enrollments__student=user,
        visibility=Task.Visibility.SHARED,
    ).distinct().order_by('-updated_at')


def build_share_menu(user):
    if user.role != user.Role.STUDENT:
        return None
    menu = {
        'journal': list(get_shareable_journal_entries(user)[:30]),
        'habit': list(get_shareable_habits(user)[:30]),
        'goal': list(get_shareable_goals(user)[:30]),
        'task': list(get_shareable_tasks(user)[:30]),
    }
    return {
        kind: items
        for kind, items in menu.items()
        if is_module_enabled(SNAPSHOT_KIND_TO_SLUG.get(kind, ''))
    }


def list_shareable_objects(user, kind):
    menu = build_share_menu(user)
    if not menu:
        return []
    return menu.get(kind, [])


def get_shareable_object(user, kind, obj_id):
    if kind not in SNAPSHOT_KINDS:
        return None
    module_slug = SNAPSHOT_KIND_TO_SLUG.get(kind)
    if not module_slug or not is_module_enabled(module_slug):
        return None
    if kind == Post.SnapshotKind.JOURNAL:
        entry = JournalEntry.objects.filter(pk=obj_id, author=user).first()
        if entry and entry.visibility == JournalEntry.Visibility.SHARED:
            return entry
        return None
    if kind == Post.SnapshotKind.HABIT:
        habit = Habit.objects.filter(pk=obj_id, author=user).first()
        if habit and habit.visibility == Habit.Visibility.SHARED:
            return habit
        return None
    if kind == Post.SnapshotKind.GOAL:
        goal = Goal.objects.filter(pk=obj_id, visibility=Goal.Visibility.SHARED).first()
        if goal and get_goal_enrollment(user, goal):
            return goal
        return None
    if kind == Post.SnapshotKind.TASK:
        task = Task.objects.filter(pk=obj_id, visibility=Task.Visibility.SHARED).first()
        if task and get_task_enrollment(user, task):
            return task
        return None
    return None


def build_snapshot_for_object(user, obj):
    if isinstance(obj, JournalEntry):
        return build_journal_snapshot(obj)
    if isinstance(obj, Habit):
        return build_habit_snapshot(obj, user)
    if isinstance(obj, Goal):
        return build_goal_snapshot(obj, get_goal_enrollment(user, obj))
    if isinstance(obj, Task):
        return build_task_snapshot(obj, get_task_enrollment(user, obj))
    raise TypeError(f'Unsupported snapshot object: {type(obj)}')
