from django.shortcuts import redirect

from accounts.models import User

PRIVACY_EXEMPT = (
    '/account/login/',
    '/account/logout/',
    '/accounts/login/',
    '/accounts/logout/',
    '/accounts/privacy-policy/',
    '/admin/',
    '/api/',
    '/health/',
    '/static/',
    '/media/',
)

PASSWORD_CHANGE_EXEMPT = (
    '/account/login/',
    '/account/logout/',
    '/accounts/login/',
    '/accounts/logout/',
    '/accounts/password-change/',
    '/accounts/privacy-policy/',
    '/admin/',
    '/api/',
    '/health/',
    '/static/',
    '/media/',
)

TWO_FA_EXEMPT = (
    '/account/login/',
    '/account/logout/',
    '/account/two_factor/',
    '/accounts/login/',
    '/accounts/logout/',
    '/accounts/privacy-policy/',
    '/accounts/password-change/',
    '/admin/',
    '/api/',
    '/health/',
    '/static/',
    '/media/',
)

AUDIT_SKIP = ('/static/', '/media/', '/api/health', '/favicon', '/health/')

WELCOME_EXEMPT = (
    '/account/login/',
    '/account/logout/',
    '/account/two_factor/',
    '/accounts/login/',
    '/accounts/logout/',
    '/accounts/welcome/',
    '/accounts/privacy-policy/',
    '/accounts/password-change/',
    '/admin/',
    '/api/',
    '/health/',
    '/static/',
    '/media/',
)


class PrivacyPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            exempt = any(request.path.startswith(p) for p in PRIVACY_EXEMPT)
            if not exempt and not request.user.privacy_policy_accepted:
                return redirect('accounts:privacy_policy')
        return self.get_response(request)


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            exempt = any(request.path.startswith(p) for p in PASSWORD_CHANGE_EXEMPT)
            if not exempt and request.user.must_change_password:
                return redirect('accounts:password_change_required')
        return self.get_response(request)


class Require2FAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if request.user.role in (User.Role.ADMIN, User.Role.TEACHER):
                exempt = any(request.path.startswith(p) for p in TWO_FA_EXEMPT)
                dev_bypass = _dev_auth_bypass(request)
                if not exempt and not dev_bypass:
                    from django_otp import user_has_device

                    if not user_has_device(request.user):
                        return redirect('two_factor:setup')
        return self.get_response(request)


class WelcomeMiddleware:
    """Redirect to first-login onboarding until welcome_seen is set."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            exempt = any(request.path.startswith(p) for p in WELCOME_EXEMPT)
            if not exempt and not request.user.welcome_seen:
                return redirect('accounts:welcome')
        return self.get_response(request)


class AuditLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.user.is_authenticated
            and request.method == 'POST'
            and not any(request.path.startswith(p) for p in AUDIT_SKIP)
        ):
            try:
                from .models import AuditLog

                ip = (
                    request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                    or request.META.get('REMOTE_ADDR')
                )
                AuditLog.objects.create(
                    user=request.user,
                    user_email=request.user.email,
                    method=request.method,
                    path=request.path,
                    ip_address=ip or None,
                )
            except Exception:
                pass
        return response


def _dev_auth_bypass(request) -> bool:
    from .dev_seed import DEV_AUTH_BYPASS_SESSION_KEY, dev_seed_enabled

    return dev_seed_enabled() and bool(request.session.get(DEV_AUTH_BYPASS_SESSION_KEY))
