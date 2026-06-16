"""In-app/email/Slack notifications for learning entity assignments."""

from __future__ import annotations

from django.conf import settings
from django.urls import reverse

from accounts.models import User

from .constants import EventType
from .dispatcher import dispatch_event


def _actor_label(actor):
    if actor is None:
        return 'Staff'
    return actor.display_name


def _email_body(*, recipient, actor_name, entity_label, title, description, url):
    site = getattr(settings, 'SITE_URL', '').rstrip('/')
    full_url = f'{site}{url}' if url else site
    lines = [
        f'Hi {recipient.display_name},',
        '',
        f'{actor_name} assigned you a {entity_label}: {title}',
    ]
    if description:
        lines.extend(['', description.strip()])
    lines.extend(['', f'View it here: {full_url}', '', '— Powercoders Team'])
    return '\n'.join(lines)


def _as_recipients(students):
    if not students:
        return []
    if hasattr(students, 'filter'):
        return list(students)
    if isinstance(students, User):
        return [students]
    return list(students)


def _dispatch_assignment(
    *,
    event_type,
    recipients,
    actor,
    entity_label,
    title,
    description,
    url,
    dedupe_prefix,
    emoji,
):
    actor_name = _actor_label(actor)
    notification_title = f'New {entity_label}: {title}'
    slack_text = f'{emoji} *{actor_name}* assigned you a {entity_label}: *{title}*'

    for recipient in _as_recipients(recipients):
        dispatch_event(
            event_type=event_type,
            recipients=[recipient],
            title=notification_title,
            body=description or '',
            url=url,
            dedupe_key=f'{dedupe_prefix}:{recipient.pk}',
            email_subject=notification_title,
            email_body=_email_body(
                recipient=recipient,
                actor_name=actor_name,
                entity_label=entity_label,
                title=title,
                description=description,
                url=url,
            ),
            slack_text=slack_text,
        )


def notify_task_assigned(*, task, students, actor):
    from tasks.models import Task

    if task.visibility != Task.Visibility.SHARED:
        return
    url = reverse('tasks:task_detail', args=[task.pk])
    _dispatch_assignment(
        event_type=EventType.NEW_TASK,
        recipients=students,
        actor=actor,
        entity_label='task',
        title=task.title,
        description=task.description,
        url=url,
        dedupe_prefix=f'task-assigned:{task.pk}',
        emoji='📋',
    )


def notify_goal_assigned(*, goal, students, actor):
    from goals.models import Goal

    if goal.visibility != Goal.Visibility.SHARED:
        return
    url = reverse('goals:detail', args=[goal.pk])
    _dispatch_assignment(
        event_type=EventType.NEW_GOAL,
        recipients=students,
        actor=actor,
        entity_label='goal',
        title=goal.title,
        description=goal.description,
        url=url,
        dedupe_prefix=f'goal-assigned:{goal.pk}',
        emoji='🎯',
    )


def notify_workflow_assigned(*, workflow, students, actor):
    if workflow.is_private:
        return
    url = reverse('workflows:detail', args=[workflow.pk])
    _dispatch_assignment(
        event_type=EventType.NEW_WORKFLOW,
        recipients=students,
        actor=actor,
        entity_label='workflow',
        title=workflow.title,
        description=workflow.description,
        url=url,
        dedupe_prefix=f'workflow-assigned:{workflow.pk}',
        emoji='🧭',
    )
