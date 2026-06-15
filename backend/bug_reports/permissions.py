from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from cohorts.permissions import user_is_admin
from config.module_access import is_module_enabled


def module_enabled_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_module_enabled('bug_reports'):
            from config.views import module_disabled_view

            return module_disabled_view(request, 'bug_reports')
        return view_func(request, *args, **kwargs)

    return wrapper


def admin_inbox_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not user_is_admin(request.user):
            return redirect('dashboard:dashboard')
        if not is_module_enabled('bug_reports'):
            from config.views import module_disabled_view

            return module_disabled_view(request, 'bug_reports')
        return view_func(request, *args, **kwargs)

    return wrapper
