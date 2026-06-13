from django.contrib.auth import get_user_model
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice

User = get_user_model()

DEFAULT_PASSWORD = 'test-pass-123'


def make_user(
    email,
    *,
    role=User.Role.STUDENT,
    display_name=None,
    password=DEFAULT_PASSWORD,
    cohort=None,
    group=None,
    bypass_onboarding=True,
    **extra,
):
    display_name = display_name or role.capitalize()
    user = User.objects.create_user(
        email=email,
        password=password,
        display_name=display_name,
        role=role,
        **extra,
    )
    if bypass_onboarding:
        # Test users skip onboarding gates (privacy policy, welcome, forced password change).
        user.privacy_policy_accepted = True
        user.privacy_policy_accepted_at = timezone.now()
        user.welcome_seen = True
        user.must_change_password = False
        user.save(
            update_fields=[
                'privacy_policy_accepted',
                'privacy_policy_accepted_at',
                'welcome_seen',
                'must_change_password',
            ]
        )
    if cohort is not None or group is not None:
        user.cohort = cohort
        user.group = group
        user.save(update_fields=['cohort', 'group'])
    return user


def make_student(email, *, cohort=None, group=None, **kwargs):
    return make_user(
        email,
        role=User.Role.STUDENT,
        cohort=cohort,
        group=group,
        **kwargs,
    )


def make_teacher(email, **kwargs):
    return make_user(email, role=User.Role.TEACHER, **kwargs)


def make_admin(email, **kwargs):
    kwargs.setdefault('is_staff', True)
    kwargs.setdefault('is_superuser', True)
    return make_user(email, role=User.Role.ADMIN, **kwargs)


def confirm_totp_for_staff(user):
    """Staff routes require a confirmed TOTP device (Require2FAMiddleware)."""
    if user.role in (user.Role.TEACHER, user.Role.ADMIN):
        TOTPDevice.objects.get_or_create(
            user=user,
            name='test-device',
            defaults={'confirmed': True},
        )


def login_as(client, user, *, password=DEFAULT_PASSWORD):
    """Log in for view tests without hitting Axes or the 2FA login form."""
    del password  # force_login does not verify password; use make_user password for POST tests
    confirm_totp_for_staff(user)
    client.force_login(user)
    return True
