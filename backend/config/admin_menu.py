"""Administration dropdown — admin/superuser only."""

from __future__ import annotations

from django.urls import NoReverseMatch, reverse

from config.module_access import is_module_enabled
from config.nav import NavItem
from cohorts.permissions import user_is_admin

ADMIN_NAV_MENU_LABEL = 'Administration'

ADMIN_NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem('Cohorts & Groups', 'accounts:cohort_list'),
    NavItem('Student Progress', 'accounts:student_progress'),
    NavItem('File storage', 'accounts:storage_settings'),
    NavItem('Bug Reports', 'bug_reports:report_list'),
    NavItem('Users', 'accounts:user_list'),
    NavItem('Create User', 'accounts:user_create'),
    NavItem('Import Users (CSV)', 'accounts:user_import'),
    NavItem('Audit Log', 'admin:accounts_auditlog_changelist'),
    NavItem('Django Admin', 'admin:index'),
)


def _resolve_url(url_name: str) -> str | None:
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return None


def admin_nav_items(*, user) -> list[dict[str, str]]:
    if not user_is_admin(user):
        return []
    items: list[dict[str, str]] = []
    for entry in ADMIN_NAV_ITEMS:
        if entry.url_name == 'bug_reports:report_list' and not is_module_enabled('bug_reports'):
            continue
        url = _resolve_url(entry.url_name)
        if url is None:
            continue
        items.append({'label': entry.label, 'url': url, 'url_name': entry.url_name})
    return items
