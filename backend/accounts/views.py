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
from .models import User


def _build_checklist(user):
    """Onboarding checklist for students (DB-backed progress, no extra model)."""
    from django.urls import reverse

    if user.role != User.Role.STUDENT:
        return [], 0

    from goals.models import Goal, GoalEnrollment
    from group_space.models import Post
    from journal.models import JournalEntry
    from reflections.models import Reflection
    from tasks.models import TaskEnrollment

    steps = [
        {
            'key': 'profile_photo',
            'label': 'Upload a profile photo',
            'description': 'Add your photo so your teacher knows who you are',
            'url': reverse('accounts:profile'),
            'done': user.has_custom_avatar,
            'emoji': '🖼️',
            'bg_class': 'bg-blue-50',
        },
        {
            'key': 'first_journal',
            'label': 'Write your first journal entry',
            'description': 'Capture what you learned today — takes 2 minutes',
            'url': reverse('journal:list'),
            'done': JournalEntry.objects.filter(author=user).exists(),
            'emoji': '📓',
            'bg_class': 'bg-amber-50',
        },
        {
            'key': 'first_goal',
            'label': 'Set your first learning goal',
            'description': 'Define a Hard Skill, Soft Skill, or Language goal',
            'url': reverse('goals:list'),
            'done': (
                Goal.objects.filter(author=user).exists()
                or GoalEnrollment.objects.filter(student=user).exists()
            ),
            'emoji': '🎯',
            'bg_class': 'bg-purple-50',
        },
        {
            'key': 'first_task',
            'label': 'Create or complete a task',
            'description': 'Personal tasks and teacher assignments live in Tasks',
            'url': reverse('tasks:task_list'),
            'done': TaskEnrollment.objects.filter(student=user).exists(),
            'emoji': '✅',
            'bg_class': 'bg-blue-50',
        },
        {
            'key': 'first_reflection',
            'label': 'Submit your first reflection',
            'description': 'Your weekly check-in helps your teacher support you',
            'url': reverse('reflections:list'),
            'done': Reflection.objects.filter(author=user).exists(),
            'emoji': '🔄',
            'bg_class': 'bg-green-50',
        },
        {
            'key': 'first_group_post',
            'label': 'Say hello in Group Space',
            'description': 'Connect with your cohort in group chat',
            'url': reverse('group_space:feed'),
            'done': Post.objects.filter(author=user).exists(),
            'emoji': '👥',
            'bg_class': 'bg-[#B23149]/10',
        },
    ]
    done_count = sum(1 for step in steps if step['done'])
    return steps, done_count


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            if request.POST.get('remove_avatar') and user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
            user.save()
            messages.success(request, 'Profile updated.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def onboarding(request):
    """First-login tutorial (Ali-style 3-step flow). URL name kept as accounts:welcome."""
    user = request.user
    is_student = user.role == User.Role.STUDENT
    if request.method == 'POST':
        user.welcome_seen = True
        user.save(update_fields=['welcome_seen'])
        return redirect('dashboard:dashboard')
    steps, done_count = _build_checklist(user)
    return render(
        request,
        'accounts/welcome.html',
        {
            'checklist_steps': steps,
            'checklist_done': done_count,
            'show_checklist_step': is_student,
            'onboarding_total_steps': 3 if is_student else 2,
        },
    )


welcome = onboarding


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
