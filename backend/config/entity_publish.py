"""Scheduled publication for draft workflows, tasks, and goals."""

from __future__ import annotations

import logging
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

ENTITY_WORKFLOW = 'workflow'
ENTITY_TASK = 'task'
ENTITY_GOAL = 'goal'


def entity_type_for(obj) -> str:
    from goals.models import Goal
    from tasks.models import Task
    from workflows.models import Workflow

    if isinstance(obj, Workflow):
        return ENTITY_WORKFLOW
    if isinstance(obj, Task):
        return ENTITY_TASK
    if isinstance(obj, Goal):
        return ENTITY_GOAL
    raise TypeError(f'Unsupported entity type: {type(obj)}')


def is_draft_entity(entity) -> bool:
    from goals.models import Goal
    from tasks.models import Task
    from workflows.models import Workflow

    if isinstance(entity, Workflow):
        return entity.is_private
    if isinstance(entity, (Task, Goal)):
        return entity.is_staff_assigned and entity.visibility == entity.Visibility.PRIVATE
    return False


def _published_visibility_value(entity):
    from goals.models import Goal
    from tasks.models import Task
    from workflows.models import Workflow

    if isinstance(entity, Workflow):
        return Workflow.Visibility.PUBLIC
    return entity.Visibility.SHARED


def visibility_is_draft(entity_class, visibility: str) -> bool:
    from goals.models import Goal
    from tasks.models import Task
    from workflows.models import Workflow

    if entity_class is Workflow:
        return visibility == Workflow.Visibility.PRIVATE
    return visibility == Goal.Visibility.PRIVATE


def should_defer_assignment_notifications(entity) -> bool:
    return is_draft_entity(entity) and bool(entity.scheduled_publish_at)


def scheduled_publish_form_value(entity) -> str:
    if not getattr(entity, 'scheduled_publish_at', None):
        return ''
    return timezone.localtime(entity.scheduled_publish_at).strftime('%Y-%m-%dT%H:%M')


def scheduled_publish_picker_context(entity) -> dict:
    return {
        'show_scheduled_publish_fields': is_draft_entity(entity) or bool(entity.scheduled_publish_at),
        'scheduled_publish_at_value': scheduled_publish_form_value(entity),
        'scheduled_publish_enabled': bool(entity.scheduled_publish_at),
    }


def scheduled_publish_form_defaults() -> dict:
    return {
        'show_scheduled_publish_fields': True,
        'scheduled_publish_at_value': '',
        'scheduled_publish_enabled': False,
    }


def scheduled_publish_detail_context(entity) -> dict:
    if not getattr(entity, 'scheduled_publish_at', None):
        return {}
    return {'scheduled_publish_at': entity.scheduled_publish_at}


def parse_scheduled_publish_at(post) -> datetime | None:
    if post.get('enable_scheduled_publish') != 'on':
        return None
    raw = (post.get('scheduled_publish_at') or '').strip()
    if not raw:
        raise ValidationError('Select a date and time for scheduled publication.')
    parsed = _parse_datetime_local(raw)
    if parsed is None:
        raise ValidationError('Invalid publication date and time.')
    if parsed <= timezone.now():
        raise ValidationError('Publication time must be in the future.')
    return parsed


def _parse_datetime_local(raw: str) -> datetime | None:
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            naive = datetime.strptime(raw, fmt)
            return timezone.make_aware(naive, timezone.get_current_timezone())
        except ValueError:
            continue
    from django.utils.dateparse import parse_datetime

    parsed = parse_datetime(raw)
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def cancel_scheduled_publish(entity, *, save: bool = True) -> None:
    task_id = (getattr(entity, 'scheduled_publish_task_id', '') or '').strip()
    if task_id:
        try:
            from config.celery import app

            app.control.revoke(task_id)
        except Exception:
            logger.warning('Could not revoke publish task %s', task_id, exc_info=True)
    entity.scheduled_publish_at = None
    entity.scheduled_publish_task_id = ''
    if save:
        entity.save(update_fields=['scheduled_publish_at', 'scheduled_publish_task_id', 'updated_at'])


def _enqueue_publish_task(entity) -> None:
    from config.tasks import publish_scheduled_entity_task

    result = publish_scheduled_entity_task.apply_async(
        args=[entity_type_for(entity), entity.pk],
        eta=entity.scheduled_publish_at,
    )
    entity.scheduled_publish_task_id = result.id or ''
    entity.save(update_fields=['scheduled_publish_task_id', 'updated_at'])


def notify_students_for_entity(entity, *, actor, students=None) -> None:
    from accounts.notifications.scheduling import (
        schedule_goal_assigned,
        schedule_task_assigned,
        schedule_workflow_assigned,
    )
    from goals.models import Goal
    from tasks.models import Task
    from workflows.models import Workflow
    from workflows.permissions import get_workflow_assigned_students

    if students is None:
        if isinstance(entity, Workflow):
            students = get_workflow_assigned_students(entity)
        elif isinstance(entity, Task):
            from accounts.models import User

            students = User.objects.filter(
                pk__in=entity.enrollments.values_list('student_id', flat=True),
                role=User.Role.STUDENT,
                is_active=True,
            )
        elif isinstance(entity, Goal):
            from accounts.models import User

            students = User.objects.filter(
                pk__in=entity.enrollments.values_list('student_id', flat=True),
                role=User.Role.STUDENT,
                is_active=True,
            )
        else:
            students = []

    if isinstance(entity, Workflow):
        schedule_workflow_assigned(workflow=entity, students=students, actor=actor)
    elif isinstance(entity, Task):
        schedule_task_assigned(task=entity, students=students, actor=actor)
    elif isinstance(entity, Goal):
        schedule_goal_assigned(goal=entity, students=students, actor=actor)


def apply_publish_schedule_from_post(
    *,
    entity,
    post,
    actor=None,
    previous_visibility: str | None = None,
    students=None,
) -> None:
    """Sync schedule fields; send notifications when manually published from draft."""
    if not is_draft_entity(entity):
        was_draft = (
            previous_visibility is not None
            and visibility_is_draft(entity.__class__, previous_visibility)
        )
        cancel_scheduled_publish(entity)
        if was_draft:
            notify_students_for_entity(entity, actor=actor, students=students)
        return

    schedule_at = parse_scheduled_publish_at(post)
    if schedule_at:
        cancel_scheduled_publish(entity, save=False)
        entity.scheduled_publish_at = schedule_at
        entity.scheduled_publish_task_id = ''
        entity.save(update_fields=['scheduled_publish_at', 'scheduled_publish_task_id', 'updated_at'])
        _enqueue_publish_task(entity)
        return

    cancel_scheduled_publish(entity)


def publish_entity_now(entity_type: str, entity_pk: int) -> bool:
    from goals.models import Goal
    from tasks.models import Task
    from workflows.models import Workflow

    loaders = {
        ENTITY_WORKFLOW: Workflow,
        ENTITY_TASK: Task,
        ENTITY_GOAL: Goal,
    }
    model = loaders.get(entity_type)
    if model is None:
        return False

    with transaction.atomic():
        entity = model.objects.select_for_update().get(pk=entity_pk)
        if not entity.scheduled_publish_at:
            return False
        if not is_draft_entity(entity):
            cancel_scheduled_publish(entity)
            return False

        entity.visibility = _published_visibility_value(entity)
        actor_id = getattr(entity, 'created_by_id', None)
        entity.scheduled_publish_at = None
        entity.scheduled_publish_task_id = ''
        entity.save(
            update_fields=['visibility', 'scheduled_publish_at', 'scheduled_publish_task_id', 'updated_at'],
        )

    from accounts.models import User

    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    notify_students_for_entity(entity, actor=actor)
    return True
