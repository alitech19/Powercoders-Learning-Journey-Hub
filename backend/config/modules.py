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
