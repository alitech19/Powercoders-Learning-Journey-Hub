from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


def normalize_page_url(request, raw_from: str = '') -> tuple[str, str]:
    """Return (full_url, path_with_query) validated against this site."""
    site = getattr(settings, 'SITE_URL', '').rstrip('/')
    candidate = (raw_from or '').strip()

    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host(), urlparse(site).netloc},
        require_https=request.is_secure(),
    ):
        parsed = urlparse(candidate)
        path = parsed.path or '/'
        if parsed.query:
            path = f'{path}?{parsed.query}'
        full = candidate if candidate.startswith(('http://', 'https://')) else urljoin(site + '/', candidate.lstrip('/'))
        return full[:2048], path[:512]

    referer = (request.META.get('HTTP_REFERER') or '').strip()
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host(), urlparse(site).netloc},
        require_https=request.is_secure(),
    ):
        parsed = urlparse(referer)
        path = parsed.path or '/'
        if parsed.query:
            path = f'{path}?{parsed.query}'
        return referer[:2048], path[:512]

    path = request.path
    full = f'{site}{path}' if site else request.build_absolute_uri(path)
    return full[:2048], path[:512]
