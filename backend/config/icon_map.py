"""
App-wide volumetric icon glyphs — single source for `_volumetric_icon.html`.

Phase 2b: duotone SVG glyphs inside styled tiles (`includes/icons/_glyph.html`).
"""

from __future__ import annotations

ICON_KEYS: frozenset[str] = frozenset({
    'workflows',
    'tasks',
    'goals',
    'reflections',
    'journal',
    'habits',
    'chat',
    'resources',
    'learning',
    'wellbeing',
    'notifications',
    'cohorts',
    'users',
    'mail',
    'alert',
    'profile',
    'lock',
})

URL_ICON_KEYS: dict[str, str] = {
    'workflows:list': 'workflows',
    'tasks:task_list': 'tasks',
    'goals:list': 'goals',
    'habits:list': 'habits',
    'reflections:list': 'reflections',
    'journal:list': 'journal',
    'group_space:feed': 'chat',
    'resources:index': 'resources',
}

ICON_SIZES: frozenset[str] = frozenset({'xs', 'sm', 'md', 'lg'})
ICON_VARIANTS: frozenset[str] = frozenset({'brand', 'cream', 'soft', 'nav'})

DEFAULT_SIZE = 'md'
DEFAULT_VARIANT = 'brand'


def is_valid_icon_key(icon_key: str) -> bool:
    return icon_key in ICON_KEYS


def icon_key_for_url(url_name: str) -> str:
    return URL_ICON_KEYS.get(url_name, '')


def normalize_size(size: str | None) -> str:
    if size in ICON_SIZES:
        return size
    return DEFAULT_SIZE


def normalize_variant(variant: str | None) -> str:
    if variant in ICON_VARIANTS:
        return variant
    return DEFAULT_VARIANT
