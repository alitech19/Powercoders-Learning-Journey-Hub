from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .data_export import build_user_data_markdown
from .forms import NotificationSettingsForm
from .models import Notification, SlackIntegration
from .notifications.settings import get_notification_settings
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
    if request.method == 'POST':
        form = NotificationSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification settings updated.')
            return redirect('accounts:notification_settings')
    else:
        form = NotificationSettingsForm(instance=settings)
    return render(
        request,
        'accounts/notification_settings.html',
        {
            'form': form,
            'slack_configured': slack_oauth_configured(),
            'slack_integration': SlackIntegration.objects.filter(user=request.user).first(),
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
