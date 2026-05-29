"""
django-axes helpers for two_factor login (wizard prefix ``auth-``).

Django's auth backend passes credentials with key ``username``; the login form
POST uses ``auth-username``. Axes must read both.
"""

from __future__ import annotations

from typing import Any


def get_axes_username(request, credentials: dict[str, Any] | None = None) -> str | None:
    if credentials:
        username = credentials.get('username')
        if username:
            return username
        username = credentials.get('auth-username')
        if username:
            return username

    if request is None:
        return None

    post = getattr(request, 'POST', None)
    if post:
        username = post.get('auth-username') or post.get('username')
        if username:
            return username

    return None
