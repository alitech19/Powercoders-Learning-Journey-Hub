from __future__ import annotations

from django.core.cache import cache

from .models import IntegratedModule
from .modules import MODULE_REGISTRY

_CACHE_KEY = 'powerhub:enabled_module_slugs'
_CACHE_TTL = 60


def _default_enabled_slugs() -> set[str]:
    return {spec.slug for spec in MODULE_REGISTRY}


def enabled_slugs() -> set[str]:
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return set(cached)

    rows = IntegratedModule.objects.filter(is_enabled=True).values_list('slug', flat=True)
    slugs = set(rows)
    if not slugs:
        slugs = _default_enabled_slugs()
    cache.set(_CACHE_KEY, list(slugs), _CACHE_TTL)
    return slugs


def is_module_enabled(slug: str) -> bool:
    if slug not in {spec.slug for spec in MODULE_REGISTRY}:
        return True
    return slug in enabled_slugs()


def invalidate_module_cache() -> None:
    cache.delete(_CACHE_KEY)
