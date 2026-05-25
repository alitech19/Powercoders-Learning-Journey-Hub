import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


def _dev_login_enabled():
    return getattr(settings, 'DEBUG', False) and getattr(settings, 'ENABLE_DEV_LOGIN', False)


def _dev_login(request, env_email_key, fallback_email):
    if not _dev_login_enabled():
        return HttpResponseForbidden('Dev login is disabled.')

    User = get_user_model()
    email = os.environ.get(env_email_key, fallback_email)
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        messages.error(request, f'Dev user {email} not found. Run: manage.py create_dev_users')
        return redirect('login')

    login(request, user)
    return redirect(settings.LOGIN_REDIRECT_URL)


@require_POST
def dev_login_student(request):
    return _dev_login(request, 'DEV_STUDENT_EMAIL', 'student@example.com')


@require_POST
def dev_login_teacher(request):
    return _dev_login(request, 'DEV_TEACHER_EMAIL', 'teacher@example.com')


@require_POST
def dev_login_admin(request):
    return _dev_login(request, 'DEV_ADMIN_EMAIL', 'admin@example.com')
