"""Validate client-submitted technical context (privacy-conscious subset)."""

from __future__ import annotations

import json
import re

ALLOWED_KEYS = frozenset(
    {
        'browser',
        'os',
        'viewport',
        'screen',
        'pixel_ratio',
        'color_scheme',
        'timezone',
        'language',
        'touch',
        'connection',
    }
)

_SHORT_TEXT = re.compile(r'^[\w\s./+\-():×]{1,64}$', re.UNICODE)
_TIMEZONE = re.compile(r'^[A-Za-z_]+/[A-Za-z_]+$|^UTC$')
_DIMENSIONS = re.compile(r'^\d{1,5}×\d{1,5}$')


def parse_client_context(raw) -> dict:
    if not raw:
        return {}
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    if not isinstance(data, dict):
        return {}

    cleaned: dict = {}
    for key, value in data.items():
        if key not in ALLOWED_KEYS:
            continue
        if key == 'pixel_ratio':
            try:
                ratio = float(value)
            except (TypeError, ValueError):
                continue
            if 0.5 <= ratio <= 5:
                cleaned[key] = round(ratio, 2)
            continue
        if key == 'touch':
            cleaned[key] = bool(value)
            continue
        if key in ('viewport', 'screen'):
            text = str(value).strip().replace('x', '×')
            if _DIMENSIONS.match(text):
                cleaned[key] = text
            continue
        if key == 'timezone':
            text = str(value).strip()[:64]
            if _TIMEZONE.match(text):
                cleaned[key] = text
            continue
        if key == 'color_scheme' and value in ('light', 'dark'):
            cleaned[key] = value
            continue
        if key == 'connection' and value in ('slow-2g', '2g', '3g', '4g'):
            cleaned[key] = value
            continue
        text = str(value).strip()[:64]
        if text and _SHORT_TEXT.match(text):
            cleaned[key] = text
    return cleaned


def format_client_context(context: dict) -> list[tuple[str, str]]:
    if not context:
        return []
    labels = {
        'browser': 'Browser',
        'os': 'OS',
        'viewport': 'Viewport',
        'screen': 'Screen',
        'pixel_ratio': 'Pixel ratio',
        'color_scheme': 'Color scheme',
        'timezone': 'Timezone',
        'language': 'Language',
        'touch': 'Touch',
        'connection': 'Connection',
    }
    rows: list[tuple[str, str]] = []
    for key in (
        'browser',
        'os',
        'viewport',
        'screen',
        'pixel_ratio',
        'color_scheme',
        'timezone',
        'language',
        'touch',
        'connection',
    ):
        if key not in context:
            continue
        value = context[key]
        if key == 'touch':
            value = 'Yes' if value else 'No'
        elif key == 'pixel_ratio':
            value = f'{float(value):.1f}'
        rows.append((labels[key], str(value)))
    return rows
