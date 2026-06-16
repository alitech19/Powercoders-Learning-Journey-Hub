"""Admin-only view for global notification configuration."""

from django import forms
from django.contrib import messages
from django.utils import timezone

from accounts.decorators import admin_required
from django.shortcuts import redirect, render

from .models import NotificationConfig

_INPUT_CLASS = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-[#B23149] focus:border-[#B23149]'
)
_CHECKBOX_CLASS = (
    'rounded border-gray-300 dark:border-gray-600 text-[#B23149] focus:ring-[#B23149]'
)


class NotificationConfigForm(forms.ModelForm):
    class Meta:
        model = NotificationConfig
        fields = [
            'deadline_reminders_enabled',
            'reminder_offset_24h',
            'reminder_offset_2h',
            'reminder_offset_overdue',
            'reflection_digest_enabled',
            'reflection_reminder_day',
            'reflection_reminder_hour',
            'reflection_reminder_minute',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault('class', _CHECKBOX_CLASS)
            elif isinstance(w, (forms.TextInput, forms.NumberInput, forms.Select)):
                w.attrs.setdefault('class', _INPUT_CLASS)

    def clean_reflection_reminder_hour(self):
        val = self.cleaned_data.get('reflection_reminder_hour', 0)
        if not 0 <= val <= 23:
            raise forms.ValidationError('Hour must be 0–23.')
        return val

    def clean_reflection_reminder_minute(self):
        val = self.cleaned_data.get('reflection_reminder_minute', 0)
        if not 0 <= val <= 59:
            raise forms.ValidationError('Minute must be 0–59.')
        return val


@admin_required
def notification_config_view(request):
    config = NotificationConfig.get()

    if request.method == 'POST':
        if 'run_reminders' in request.POST:
            return _run_reminders_now(request, config)

        form = NotificationConfigForm(request.POST, instance=config)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.updated_by = request.user
            instance.save()
            _sync_beat_schedules(instance)
            messages.success(request, 'Notification settings saved.')
            return redirect('config:notification_config')
    else:
        form = NotificationConfigForm(instance=config)

    return render(
        request,
        'config/notification_config.html',
        {'form': form, 'config': config},
    )


def _run_reminders_now(request, config):
    if not config.deadline_reminders_enabled:
        messages.warning(request, 'Deadline reminders are disabled — enable them first.')
        return redirect('config:notification_config')
    try:
        from accounts.notifications.deadline_reminders import send_deadline_reminders
        send_deadline_reminders()
        config.record_run()
        messages.success(request, 'Deadline reminders dispatched successfully.')
    except Exception as exc:
        config.record_run(error=str(exc))
        messages.error(request, f'Error running reminders: {exc}')
    return redirect('config:notification_config')


def _sync_beat_schedules(config):
    """Update or create django-celery-beat periodic tasks to match config."""
    try:
        from django_celery_beat.models import CrontabSchedule, PeriodicTask
        import json

        _sync_reflection_digest(config, CrontabSchedule, PeriodicTask)
        _sync_deadline_reminders(config, CrontabSchedule, PeriodicTask)
    except Exception:
        pass


def _sync_reflection_digest(config, CrontabSchedule, PeriodicTask):
    dow_map = {
        'monday': '1', 'tuesday': '2', 'wednesday': '3',
        'thursday': '4', 'friday': '5', 'saturday': '6', 'sunday': '0',
    }
    import json

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
    import json

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
