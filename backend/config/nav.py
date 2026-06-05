"""
Integrated app navigation — single source for navbar and metric column order.

Dashboard is not in nav — logo links to dashboard. Per-page help stays in page content.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.urls import NoReverseMatch, reverse

from config.icon_map import icon_key_for_url


@dataclass(frozen=True)
class NavItem:
    label: str
    url_name: str
    enabled: bool = True


@dataclass(frozen=True)
class NavGroup:
    """Top-level nav entry: dropdown (children) or single link (url_name)."""

    label: str
    children: tuple[NavItem, ...] = ()
    url_name: str | None = None
    default_url_name: str | None = None

    @property
    def is_dropdown(self) -> bool:
        return bool(self.children)


# Product nav — [UI_LAYOUT_IMPROVEMENT_PLAN.md]
NAV_GROUPS: tuple[NavGroup, ...] = (
    NavGroup(
        'Learning',
        (
            NavItem('Workflows', 'workflows:list'),
            NavItem('Tasks', 'tasks:task_list'),
            NavItem('Goals', 'goals:list'),
            NavItem('Habits', 'habits:list'),
        ),
        default_url_name='workflows:list',
    ),
    NavGroup(
        'Wellbeing',
        (
            NavItem('Reflections', 'reflections:list'),
            NavItem('Journal', 'journal:list'),
        ),
        default_url_name='reflections:list',
    ),
    NavGroup('Group Space', url_name='group_space:feed'),
    NavGroup('Resources', url_name='resources:index'),
)

def _build_nav_registry() -> tuple[NavItem, ...]:
    flat: list[NavItem] = []
    for group in NAV_GROUPS:
        if group.children:
            flat.extend(group.children)
        elif group.url_name:
            flat.append(NavItem(group.label, group.url_name))
    return tuple(flat)


# Flat registry (nav order for student metrics, share panel, etc.)
NAV_REGISTRY: tuple[NavItem, ...] = _build_nav_registry()

ADMIN_NAV_MENU_LABEL = 'Administration'

# Admin/superuser only — mirrors admin dashboard Management block
ADMIN_NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem('Cohorts & Groups', 'accounts:cohort_list'),
    NavItem('Student Progress', 'accounts:student_progress'),
    NavItem('Users', 'accounts:user_list'),
    NavItem('Create User', 'accounts:user_create'),
    NavItem('Import Users (CSV)', 'accounts:user_import'),
    NavItem('Audit Log', 'admin:accounts_auditlog_changelist'),
    NavItem('Django Admin', 'admin:index'),
)


def _app_namespace(url_name: str) -> str:
    return url_name.split(':', 1)[0]


def _resolve_url(url_name: str) -> str | None:
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return None


def _item_active(
    url_name: str,
    *,
    current_view_name: str | None,
    current_app: str | None,
) -> bool:
    if current_view_name and url_name == current_view_name:
        return True
    if current_app and _app_namespace(url_name) == current_app:
        return True
    return False


def _serialize_item(
    entry: NavItem,
    *,
    current_view_name: str | None,
    current_app: str | None,
) -> dict[str, str | bool] | None:
    if not entry.enabled:
        return None
    url = _resolve_url(entry.url_name)
    if url is None:
        return None
    return {
        'label': entry.label,
        'url': url,
        'url_name': entry.url_name,
        'icon_key': icon_key_for_url(entry.url_name),
        'active': _item_active(
            entry.url_name,
            current_view_name=current_view_name,
            current_app=current_app,
        ),
    }


def integrated_nav_items(
    *,
    current_view_name: str | None = None,
    current_app: str | None = None,
) -> list[dict[str, str | bool]]:
    """Flat nav items — backward compatibility (metrics headers, tests)."""
    items: list[dict[str, str | bool]] = []
    for entry in NAV_REGISTRY:
        row = _serialize_item(
            entry,
            current_view_name=current_view_name,
            current_app=current_app,
        )
        if row:
            items.append(row)
    return items


def integrated_nav_groups(
    *,
    current_view_name: str | None = None,
    current_app: str | None = None,
) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    for group in NAV_GROUPS:
        if group.is_dropdown:
            children: list[dict[str, str | bool]] = []
            for entry in group.children:
                row = _serialize_item(
                    entry,
                    current_view_name=current_view_name,
                    current_app=current_app,
                )
                if row:
                    children.append(row)
            if not children:
                continue
            default_url = _resolve_url(group.default_url_name or group.children[0].url_name)
            group_active = any(c['active'] for c in children)
            groups.append(
                {
                    'label': group.label,
                    'kind': 'dropdown',
                    'default_url': default_url,
                    'children': children,
                    'active': group_active,
                }
            )
        elif group.url_name:
            row = _serialize_item(
                NavItem(group.label, group.url_name),
                current_view_name=current_view_name,
                current_app=current_app,
            )
            if not row:
                continue
            groups.append(
                {
                    'label': group.label,
                    'kind': 'link',
                    'url': row['url'],
                    'url_name': row['url_name'],
                    'active': row['active'],
                }
            )
    return groups


def admin_nav_items(*, user) -> list[dict[str, str | bool]]:
    from cohorts.permissions import user_is_admin

    if not user_is_admin(user):
        return []
    items: list[dict[str, str | bool]] = []
    for entry in ADMIN_NAV_ITEMS:
        url = _resolve_url(entry.url_name)
        if url is None:
            continue
        items.append({'label': entry.label, 'url': url, 'url_name': entry.url_name})
    return items
