from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from .dev_seed import (
    DEV_AUTH_BYPASS_SESSION_KEY,
    allowed_dev_login_emails,
    dev_seed_enabled,
)
from .forms import ProfileForm


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def welcome(request):
    if request.method == 'POST':
        request.user.welcome_seen = True
        request.user.save(update_fields=['welcome_seen'])
        return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, 'accounts/welcome.html')


@login_required
def privacy_policy(request):
    if request.method == 'POST':
        request.user.privacy_policy_accepted = True
        request.user.privacy_policy_accepted_at = timezone.now()
        request.user.save(update_fields=['privacy_policy_accepted', 'privacy_policy_accepted_at'])
        return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, 'accounts/privacy_policy.html')


@login_required
def password_change_required(request):
    form = PasswordChangeForm(request.user)
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.must_change_password = False
            user.save(update_fields=['must_change_password'])
            update_session_auth_hash(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, 'accounts/password_change_required.html', {'form': form})


@require_POST
def dev_quick_login(request, email):
    if not dev_seed_enabled():
        raise Http404

    email_normalized = email.lower()
    if email_normalized not in allowed_dev_login_emails():
        raise Http404

    user = get_object_or_404(get_user_model(), email__iexact=email)
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if device is not None:
        otp_login(request, device)
    request.session[DEV_AUTH_BYPASS_SESSION_KEY] = True
    return redirect(settings.LOGIN_REDIRECT_URL)
