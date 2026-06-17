from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .data_export import build_user_data_markdown
from .forms import NotificationSettingsForm
from .models import Notification, SlackIntegration
from .notifications.settings import get_notification_settings
from .notifications.ui_constants import NOTIFICATION_EVENT_ROWS
from .slack_provider import slack_oauth_configured

User = get_user_model()


@login_required
def data_export(request):
    content = build_user_data_markdown(request.user)
    response = HttpResponse(content, content_type='text/markdown; charset=utf-8')
    safe_name = request.user.pk
    response['Content-Disposition'] = (
        f'attachment; filename="powercoders-data-{safe_name}.md"'
    )
    return response


@login_required
def delete_own_account(request):
    user = request.user
    error = None
    if request.method == 'POST':
        password = request.POST.get('password', '')
        if user.check_password(password):
            logout(request)
            user.delete()
            return redirect('accounts:account_deleted')
        error = 'Incorrect password. Please try again.'
    return render(request, 'accounts/delete_own_account.html', {'error': error})


def account_deleted(request):
    return render(request, 'accounts/account_deleted.html')


@login_required
def notification_settings(request):
    settings = get_notification_settings(request.user)
    slack_integration = SlackIntegration.objects.filter(user=request.user).first()
    slack_connected = bool(slack_integration and slack_integration.is_connected)
    if request.method == 'POST':
        form = NotificationSettingsForm(
            request.POST,
            instance=settings,
            slack_connected=slack_connected,
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification settings updated.')
            next_url = request.POST.get('next', '').strip()
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('accounts:notification_settings')
    else:
        form = NotificationSettingsForm(instance=settings, slack_connected=slack_connected)
    notification_rows = [
        {
            'label': row['label'],
            'in_app': form[row['in_app_field']],
            'email': form[row['email_field']],
            'slack': form[row['slack_field']],
        }
        for row in NOTIFICATION_EVENT_ROWS
    ]
    return render(
        request,
        'accounts/notification_settings.html',
        {
            'form': form,
            'notification_rows': notification_rows,
            'slack_configured': slack_oauth_configured(),
            'slack_integration': slack_integration,
            'slack_connected': slack_connected,
        },
    )


@login_required
def notifications_list(request):
    notifs = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return render(request, 'accounts/notifications.html', {'notifications': notifs})


@login_required
@require_POST
def notification_mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    if notif.url:
        return redirect(notif.url)
    return redirect('accounts:notifications')
