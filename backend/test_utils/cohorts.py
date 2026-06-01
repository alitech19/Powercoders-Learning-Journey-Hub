from datetime import date, timedelta

from django.contrib.auth import get_user_model

from cohorts.models import Cohort, Group, GroupTeacher

_SYSTEM_USER_EMAIL = 'test-system@powerhub.invalid'


def _ensure_user_for_group_signals():
    """Group post_save creates a Resources container and needs a User in the DB."""
    User = get_user_model()
    if User.objects.exists():
        return
    User.objects.create_superuser(
        email=_SYSTEM_USER_EMAIL,
        password='test-system-pass',
        display_name='Test System',
    )


def make_cohort(name='Bootcamp 2026', *, status=Cohort.Status.ACTIVE, **kwargs):
    today = date.today()
    defaults = {
        'start_date': today - timedelta(days=30),
        'end_date': today + timedelta(days=90),
        'status': status,
    }
    defaults.update(kwargs)
    return Cohort.objects.create(name=name, **defaults)


def make_group(cohort, name='Group A', **kwargs):
    _ensure_user_for_group_signals()
    return Group.objects.create(cohort=cohort, name=name, **kwargs)


def assign_teacher(group, teacher, *, role=GroupTeacher.Role.TEACHER):
    return GroupTeacher.objects.create(
        group=group,
        teacher=teacher,
        role=role,
    )
