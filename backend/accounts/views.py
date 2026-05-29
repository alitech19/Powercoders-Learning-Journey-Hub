from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .dev_seed import allowed_dev_login_emails, dev_seed_enabled
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


@require_POST
def dev_quick_login(request, email):
    if not dev_seed_enabled():
        raise Http404

    email_normalized = email.lower()
    if email_normalized not in allowed_dev_login_emails():
        raise Http404

    user = get_object_or_404(get_user_model(), email__iexact=email)
    login(request, user)
    return redirect(settings.LOGIN_REDIRECT_URL)
