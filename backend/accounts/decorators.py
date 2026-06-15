"""
Role-based access decorators for staff-facing views.

Unauthenticated users go to LOGIN_URL. Wrong role → dashboard.
"""

from functools import wraps

from django.conf import settings
from django.shortcuts import redirect

from cohorts.permissions import user_is_admin, user_is_staff


def role_required(*roles):
    """Restrict a view to users whose role is in *roles."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)
            if request.user.role not in roles:
                return redirect('dashboard:dashboard')
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def _admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        if not user_is_admin(request.user):
            return redirect('dashboard:dashboard')
        return view_func(request, *args, **kwargs)

    return wrapper


def _teacher_or_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        if not (user_is_admin(request.user) or user_is_staff(request.user)):
            return redirect('dashboard:dashboard')
        return view_func(request, *args, **kwargs)

    return wrapper


admin_required = _admin_required
teacher_or_admin_required = _teacher_or_admin_required
student_required = role_required('student')
