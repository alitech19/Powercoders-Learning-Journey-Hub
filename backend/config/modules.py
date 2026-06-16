"""URL prefix → toggleable module slug registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleSpec:
    slug: str
    label: str
    url_prefix: str


MODULE_REGISTRY: tuple[ModuleSpec, ...] = (
    ModuleSpec('workflows', 'Workflows', '/workflows/'),
    ModuleSpec('tasks', 'Tasks', '/tasks/'),
    ModuleSpec('goals', 'Goals', '/goals/'),
    ModuleSpec('habits', 'Habits', '/habits/'),
    ModuleSpec('reflections', 'Reflections', '/reflections/'),
    ModuleSpec('journal', 'Journal', '/journal/'),
    ModuleSpec('group_space', 'Group Space', '/group/'),
    ModuleSpec('resources', 'Resources', '/resources/'),
    ModuleSpec('bug_reports', 'Bug reports', '/bugs/'),
)

# Nav url_name → toggle slug (config/nav.py NAV_REGISTRY order)
NAV_URL_TO_SLUG: dict[str, str] = {
    'workflows:list': 'workflows',
    'tasks:task_list': 'tasks',
    'goals:list': 'goals',
    'habits:list': 'habits',
    'reflections:list': 'reflections',
    'journal:list': 'journal',
    'group_space:feed': 'group_space',
    'resources:index': 'resources',
}

# Chat snapshot kind → toggle slug
SNAPSHOT_KIND_TO_SLUG: dict[str, str] = {
    'journal': 'journal',
    'habit': 'habits',
    'goal': 'goals',
    'task': 'tasks',
}

# Student oversight columns — same order as NAV_REGISTRY
METRIC_COLUMNS: tuple[tuple[str, str], ...] = (
    ('workflows', 'Workflows'),
    ('tasks', 'Tasks'),
    ('goals', 'Goals'),
    ('habits', 'Habits'),
    ('reflections', 'Reflections'),
    ('journal', 'Journal'),
    ('group_space', 'Group'),
    ('resources', 'Resources'),
)


def module_slug_for_nav_url(url_name: str) -> str | None:
    return NAV_URL_TO_SLUG.get(url_name)

CORE_PREFIXES: tuple[str, ...] = (
    '/admin/',
    '/accounts/',
    '/account/',
    '/health/',
    '/info/',
    '/static/',
    '/media/',
    '/sw.js',
    '/offline/',
)


def slug_for_path(path: str) -> str | None:
    for spec in sorted(MODULE_REGISTRY, key=lambda s: len(s.url_prefix), reverse=True):
        if path.startswith(spec.url_prefix):
            return spec.slug
    return None
