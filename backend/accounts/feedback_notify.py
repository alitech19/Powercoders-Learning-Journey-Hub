"""Map feedback targets to recipients and URLs for notifications."""

from django.urls import reverse

from goals.models import GoalEnrollment
from habits.models import Habit
from journal.models import JournalEntry
from reflections.models import Reflection
from tasks.models import TaskEnrollment

from .emails import notify_feedback_received


def _relative_url(name, **kwargs):
    return reverse(name, kwargs=kwargs)


def dispatch_feedback_notifications(entry):
    target = entry.content_object
    if target is None:
        return

    author = entry.author
    recipient = None
    relative_url = ''
    title = ''

    if isinstance(target, JournalEntry):
        if target.author_id == author.pk:
            return
        recipient = target.author
        relative_url = _relative_url('journal:detail', pk=target.pk)
        title = f'{author.display_name} left feedback on your journal entry "{target.title}"'

    elif isinstance(target, Reflection):
        if target.author_id == author.pk:
            return
        recipient = target.author
        relative_url = _relative_url('reflections:detail', pk=target.pk)
        title = f'{author.display_name} left feedback on your reflection "{target.title}"'

    elif isinstance(target, Habit):
        if target.author_id == author.pk:
            return
        recipient = target.author
        relative_url = _relative_url('habits:detail', pk=target.pk)
        title = f'{author.display_name} left feedback on your habit "{target.title}"'

    elif isinstance(target, GoalEnrollment):
        if target.student_id == author.pk:
            return
        recipient = target.student
        relative_url = _relative_url('goals:detail', pk=target.goal_id)
        title = f'{author.display_name} left feedback on your goal "{target.goal.title}"'

    elif isinstance(target, TaskEnrollment):
        if target.student_id == author.pk:
            return
        recipient = target.student
        relative_url = _relative_url('tasks:task_detail', pk=target.task_id)
        title = f'{author.display_name} left feedback on your task "{target.task.title}"'

    if recipient is None or not title:
        return

    notify_feedback_received(
        entry=entry,
        recipient=recipient,
        title=title,
        relative_url=relative_url,
    )
