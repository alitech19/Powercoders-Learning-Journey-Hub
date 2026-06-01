"""
Role-based access decorators for staff-facing views.

Unauthenticated users go to LOGIN_URL. Wrong role → dashboard.
"""

from functools import wraps

from django.conf import settings
from django.shortcuts import redirect


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


admin_required = role_required('admin')
teacher_or_admin_required = role_required('teacher', 'admin')
student_required = role_required('student')
