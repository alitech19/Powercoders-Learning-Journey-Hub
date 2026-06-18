"""Sync django-celery-beat periodic tasks from NotificationConfig."""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def sync_notification_schedules(config=None):
    """Create or update Beat tasks for deadline reminders and reflection digest."""
    from config.models import NotificationConfig

    config = config or NotificationConfig.get()
    try:
        from django_celery_beat.models import CrontabSchedule, PeriodicTask
    except Exception:
        logger.warning('django-celery-beat not available — skipping schedule sync')
        return

    _sync_reflection_digest(config, CrontabSchedule, PeriodicTask)
    _sync_deadline_reminders(config, CrontabSchedule, PeriodicTask)


def _sync_reflection_digest(config, CrontabSchedule, PeriodicTask):
    dow_map = {
        'monday': '1',
        'tuesday': '2',
        'wednesday': '3',
        'thursday': '4',
        'friday': '5',
        'saturday': '6',
        'sunday': '0',
    }
    dow = dow_map.get(config.reflection_reminder_day, '1')
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute=str(config.reflection_reminder_minute),
        hour=str(config.reflection_reminder_hour),
        day_of_week=dow,
        day_of_month='*',
        month_of_year='*',
        timezone='Europe/Zurich',
    )
    task, created = PeriodicTask.objects.update_or_create(
        name='Weekly missing-reflections digest',
        defaults={
            'task': 'accounts.tasks.notify_missing_reflections',
            'crontab': schedule,
            'enabled': config.reflection_digest_enabled,
            'args': json.dumps([]),
        },
    )
    if not created and task.crontab_id != schedule.pk:
        task.crontab = schedule
        task.save(update_fields=['crontab'])


def _sync_deadline_reminders(config, CrontabSchedule, PeriodicTask):
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='*',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
        timezone='Europe/Zurich',
    )
    PeriodicTask.objects.update_or_create(
        name='Hourly deadline reminders',
        defaults={
            'task': 'accounts.tasks.run_deadline_reminders_task',
            'crontab': schedule,
            'enabled': config.deadline_reminders_enabled,
            'args': json.dumps([]),
        },
    )
