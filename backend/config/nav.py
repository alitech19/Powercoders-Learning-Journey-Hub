"""
Integrated app navigation — single source for navbar and home hub.

Enable items only when the app is wired (urls + templates). Order = customer priority.
Dashboard is NOT here — it replaces `home` as `/` when integrated last.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.urls import NoReverseMatch, reverse


@dataclass(frozen=True)
class NavItem:
    label: str
    url_name: str
    enabled: bool = False


# Customer priority order (see docs/APPS_ROADMAP.md). Set enabled=True when app lands.
NAV_REGISTRY: tuple[NavItem, ...] = (
    NavItem('Workflows', 'workflows:list', enabled=True),
    NavItem('Goals', 'goals:list', enabled=True),
    NavItem('Tasks', 'tracker:task_list'),
    NavItem('Reflections', 'reflections:list'),
    NavItem('Wellbeing', 'wellbeing:list'),
    NavItem('Journal', 'journal:list'),
    NavItem('Habits', 'habits:list'),
    NavItem('Group', 'group_space:feed'),
    NavItem('Resources', 'group_space:resource_list'),
)


def integrated_nav_items() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for entry in NAV_REGISTRY:
        if not entry.enabled:
            continue
        try:
            url = reverse(entry.url_name)
        except NoReverseMatch:
            continue
        items.append({'label': entry.label, 'url': url})
    return items
