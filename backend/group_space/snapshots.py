import bleach
from django.template.loader import render_to_string
from django.utils import timezone

from goals.models import Goal
from goals.permissions import get_enrollment_for_user as get_goal_enrollment
from habits.models import Habit
from habits.services import build_habit_row, build_week_table, get_week_start
from journal.models import JournalEntry
from tasks.models import Task
from tasks.permissions import get_enrollment_for_user as get_task_enrollment

from .constants import SNAPSHOT_KINDS
from .models import Post

ALLOWED_SNAPSHOT_TAGS = [
    'p', 'strong', 'em', 'ul', 'ol', 'li', 'h3', 'h4', 'span', 'br', 'div',
]
ALLOWED_SNAPSHOT_ATTRIBUTES = {
    '*': ['class'],
    'div': ['class', 'data-width'],
}


def _clean_html(html):
    return bleach.clean(
        html,
        tags=ALLOWED_SNAPSHOT_TAGS,
        attributes=ALLOWED_SNAPSHOT_ATTRIBUTES,
        strip=True,
    )


def _render_snapshot(template_name, context):
    return _clean_html(render_to_string(template_name, context))


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
    items = []
    for subtask in enrollment.task.subtasks.all().order_by('order', 'pk'):
        items.append({'title': subtask.title, 'completed': subtask.pk in completed})
    return items


def build_journal_snapshot(entry):
    html = _render_snapshot('group_space/snapshots/journal.html', {'entry': entry})
    meta = {
        'title': entry.title,
        'kind_label': 'Journal entry',
        'entry_date': entry.entry_date.isoformat(),
    }
    return Post.SnapshotKind.JOURNAL, html, meta


def build_habit_snapshot(habit, user):
    today = timezone.localdate()
    week_start = get_week_start(today)
    row = build_habit_row(habit, today=today, week_start=week_start, can_log=False)
    html = _render_snapshot('group_space/snapshots/habit.html', {
        'habit': habit,
        'row': row,
        'week_table': build_week_table(habit, today),
    })
    meta = {'title': habit.title, 'kind_label': 'Habit', 'status': habit.status}
    return Post.SnapshotKind.HABIT, html, meta


def build_goal_snapshot(goal, enrollment):
    html = _render_snapshot('group_space/snapshots/goal.html', {
        'goal': goal,
        'enrollment': enrollment,
        'milestones': _goal_milestones(enrollment),
    })
    meta = {
        'title': goal.title,
        'kind_label': 'Goal',
        'status': enrollment.status if enrollment else '',
    }
    return Post.SnapshotKind.GOAL, html, meta


def build_task_snapshot(task, enrollment):
    html = _render_snapshot('group_space/snapshots/task.html', {
        'task': task,
        'enrollment': enrollment,
        'display_status': enrollment.status if enrollment else task.status,
        'subtasks': _task_subtasks(enrollment),
    })
    meta = {
        'title': task.title,
        'kind_label': 'Task',
        'status': enrollment.status if enrollment else task.status,
    }
    return Post.SnapshotKind.TASK, html, meta


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
    return {
        'journal': list(get_shareable_journal_entries(user)[:30]),
        'habit': list(get_shareable_habits(user)[:30]),
        'goal': list(get_shareable_goals(user)[:30]),
        'task': list(get_shareable_tasks(user)[:30]),
    }


def list_shareable_objects(user, kind):
    menu = build_share_menu(user)
    if not menu:
        return []
    return menu.get(kind, [])


def get_shareable_object(user, kind, obj_id):
    if kind not in SNAPSHOT_KINDS:
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
