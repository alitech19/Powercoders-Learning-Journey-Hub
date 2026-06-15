import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import PasswordResetView
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import ProfileForm
from .models import User

logger = logging.getLogger(__name__)


class SafePasswordResetView(PasswordResetView):
    """PasswordResetView that catches SMTP errors and redirects cleanly."""

    success_url = reverse_lazy('accounts:password_reset_done')

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception as exc:
            logger.warning('Password reset email failed: %s', exc, exc_info=True)
            return HttpResponseRedirect(str(self.success_url))


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
            'icon_key': 'profile',
        },
        {
            'key': 'first_journal',
            'label': 'Write your first journal entry',
            'description': 'Capture what you learned today — takes 2 minutes',
            'url': reverse('journal:list'),
            'done': JournalEntry.objects.filter(author=user).exists(),
            'icon_key': 'journal',
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
            'icon_key': 'goals',
        },
        {
            'key': 'first_task',
            'label': 'Create or complete a task',
            'description': 'Personal tasks and teacher assignments live in Tasks',
            'url': reverse('tasks:task_list'),
            'done': TaskEnrollment.objects.filter(student=user).exists(),
            'icon_key': 'tasks',
        },
        {
            'key': 'first_reflection',
            'label': 'Submit your first reflection',
            'description': 'Your weekly check-in helps your teacher support you',
            'url': reverse('reflections:list'),
            'done': Reflection.objects.filter(author=user).exists(),
            'icon_key': 'reflections',
        },
        {
            'key': 'first_group_post',
            'label': 'Say hello in Group Space',
            'description': 'Connect with your cohort in group chat',
            'url': reverse('group_space:feed'),
            'done': Post.objects.filter(author=user).exists(),
            'icon_key': 'chat',
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

    from google_storage.views import profile_google_context

    return render(
        request,
        'accounts/profile.html',
        {
            'form': form,
            **profile_google_context(request.user),
        },
    )


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
