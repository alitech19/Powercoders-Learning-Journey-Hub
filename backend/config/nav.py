"""
Integrated app navigation — single source for navbar.

Enable items only when the app is wired (urls + templates). Order = customer priority.
Dashboard is not in nav — logo links to dashboard. Per-page ⓘ opens contextual help.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.urls import NoReverseMatch, reverse


@dataclass(frozen=True)
class NavItem:
    label: str
    url_name: str
    enabled: bool = False


# Customer priority order (see docs/APP_PLAN.md). Set enabled=True when app lands.
NAV_REGISTRY: tuple[NavItem, ...] = (
    NavItem('Workflows', 'workflows:list', enabled=True),
    NavItem('Goals', 'goals:list', enabled=True),
    NavItem('Tasks', 'tasks:task_list', enabled=True),
    NavItem('Reflections', 'reflections:list', enabled=True),
    NavItem('Journal', 'journal:list', enabled=True),
    NavItem('Habits', 'habits:list', enabled=True),
    NavItem('Group', 'group_space:feed', enabled=True),
    NavItem('Resources', 'resources:index', enabled=True),
)


def integrated_nav_items(*, current_view_name: str | None = None) -> list[dict[str, str | bool]]:
    items: list[dict[str, str | bool]] = []
    for entry in NAV_REGISTRY:
        if not entry.enabled:
            continue
        try:
            url = reverse(entry.url_name)
        except NoReverseMatch:
            continue
        items.append(
            {
                'label': entry.label,
                'url': url,
                'url_name': entry.url_name,
                'active': entry.url_name == current_view_name,
            }
        )
    return items
