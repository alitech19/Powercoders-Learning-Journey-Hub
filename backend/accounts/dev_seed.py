"""
Development seed helpers.

WARNING: For local development only. Disable before production deploy.
See docs/PRODUCTION_CHECKLIST.md
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from django.conf import settings

PRODUCTION_CHECKLIST_PATH = 'docs/PRODUCTION_CHECKLIST.md'
DEV_AUTH_BYPASS_SESSION_KEY = 'dev_auth_bypass'


def apply_dev_user_security_bypass(user):
    """Seed/dev users skip onboarding gates (privacy, welcome, forced password change)."""
    from django.utils import timezone

    user.privacy_policy_accepted = True
    user.privacy_policy_accepted_at = timezone.now()
    user.welcome_seen = True
    user.must_change_password = False
    return user


def dev_seed_enabled() -> bool:
    return bool(getattr(settings, 'ENABLE_DEV_SEED', False))


def seed_file_path() -> Path:
    return Path(settings.DEV_SEED_FILE)


@lru_cache(maxsize=1)
def load_seed_data() -> dict:
    path = seed_file_path()
    if not path.is_file():
        raise FileNotFoundError(f'Dev seed file not found: {path}')
    with path.open(encoding='utf-8') as handle:
        return yaml.safe_load(handle)


@lru_cache(maxsize=1)
def allowed_dev_login_emails() -> frozenset[str]:
    data = load_seed_data()
    emails = set()
    for student in data.get('students', []):
        emails.add(student['email'].lower())
    for teacher in data.get('teachers', []):
        emails.add(teacher['email'].lower())
    admin_email = getattr(settings, 'DEV_SUPERUSER_EMAIL', '') or ''
    if admin_email:
        emails.add(admin_email.lower())
    return frozenset(emails)


def group_key(cohort_slug: str, group_slug: str) -> tuple[str, str]:
    return cohort_slug, group_slug


def resolve_group(groups_map: dict, cohort_slug: str, group_slug: str):
    key = group_key(cohort_slug, group_slug)
    if key not in groups_map:
        raise KeyError(f'Unknown group {cohort_slug}/{group_slug}')
    return groups_map[key]


def build_dev_login_context() -> dict:
    if not dev_seed_enabled():
        return {'dev_seed_enabled': False}

    from django.contrib.auth import get_user_model

    User = get_user_model()
    data = load_seed_data()
    teachers_by_email = {t['email'].lower(): t for t in data.get('teachers', [])}
    students = data.get('students', [])

    def user_button(email: str) -> dict | None:
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None
        return {'email': user.email, 'display_name': user.display_name}

    admin = None
    admin_email = getattr(settings, 'DEV_SUPERUSER_EMAIL', '')
    if admin_email:
        admin = user_button(admin_email)

    special = data.get('login_special', {})
    bootcamp_teacher = user_button(special.get('bootcamp_teacher_email', ''))
    global_teacher = user_button(special.get('global_teacher_email', ''))

    columns = []
    for col in data.get('login_columns', []):
        cohort_slug = col['cohort']
        group_slug = col['group']
        group_students = [
            s for s in students
            if s['cohort'] == cohort_slug and s['group'] == group_slug
        ]
        group_teacher_email = None
        for teacher in data.get('teachers', []):
            assignments = teacher.get('groups', [])
            if len(assignments) == 1:
                ref = assignments[0]
                if ref['cohort'] == cohort_slug and ref['group'] == group_slug:
                    group_teacher_email = teacher['email']
                    break

        group_name = group_slug.replace('-', ' ').title()
        for cohort in data.get('cohorts', []):
            if cohort['slug'] == cohort_slug:
                for group in cohort.get('groups', []):
                    if group['slug'] == group_slug:
                        group_name = group['name']
                        break

        columns.append({
            'title': group_name,
            'cohort_slug': cohort_slug,
            'cohort_name': _cohort_meta(data, cohort_slug)[0],
            'cohort_code': _cohort_meta(data, cohort_slug)[1],
            'teacher': user_button(group_teacher_email) if group_teacher_email else None,
            'students': [
                btn for s in group_students
                if (btn := user_button(s['email'])) is not None
            ],
        })

    cohort_sections = []
    for cohort in data.get('cohorts', []):
        cohort_columns = [c for c in columns if c['cohort_slug'] == cohort['slug']]
        if not cohort_columns:
            continue
        cohort_sections.append({
            'slug': cohort['slug'],
            'name': cohort['name'],
            'code': cohort.get('code', ''),
            'group_names': [col['title'] for col in cohort_columns],
            'columns': cohort_columns,
        })

    return {
        'dev_seed_enabled': True,
        'dev_production_checklist_path': PRODUCTION_CHECKLIST_PATH,
        'dev_login_admin': admin,
        'dev_login_bootcamp_teacher': bootcamp_teacher,
        'dev_login_global_teacher': global_teacher,
        'dev_login_cohort_sections': cohort_sections,
        'dev_login_name_legend': _name_legend(),
    }


def _cohort_meta(data: dict, cohort_slug: str) -> tuple[str, str]:
    for cohort in data.get('cohorts', []):
        if cohort['slug'] == cohort_slug:
            return cohort['name'], cohort.get('code', '')
    return cohort_slug, ''


def _name_legend() -> list[dict[str, str]]:
    return [
        {'abbr': 'ST', 'meaning': 'Student (participant)'},
        {'abbr': 'TC', 'meaning': 'Teacher (cohort staff)'},
        {'abbr': 'But', 'meaning': 'Bootcamp 2026 I cohort'},
        {'abbr': 'Con', 'meaning': 'Connecting Program cohort'},
        {'abbr': 'Bern / Zurich / Lausanne', 'meaning': 'Bootcamp location group'},
        {'abbr': 'All', 'meaning': 'Whole cohort (Connecting)'},
        {'abbr': 'TC-But-All', 'meaning': 'Teacher — all Bootcamp groups'},
        {'abbr': 'TC-All-All', 'meaning': 'Teacher — every group, both cohorts'},
    ]
