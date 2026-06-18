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
            from config.notification_schedules import sync_notification_schedules

            sync_notification_schedules(instance)
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

