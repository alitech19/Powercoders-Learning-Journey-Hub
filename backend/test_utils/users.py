from django.contrib.auth import get_user_model
from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts.dev_seed import apply_dev_user_security_bypass

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
        apply_dev_user_security_bypass(user)
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
    confirm_totp_for_staff(user)
    return client.login(username=user.email, password=password)
