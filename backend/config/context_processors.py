from .nav import (
    ADMIN_NAV_MENU_LABEL,
    admin_nav_items,
    integrated_nav_groups,
    integrated_nav_items,
)
from .page_meta import resolve_page_meta
from config import input_limits as il


def integrated_nav(request):
    resolver = getattr(request, 'resolver_match', None)
    current_view_name = resolver.view_name if resolver else None
    current_app = resolver.app_name if resolver else None
    kwargs = {
        'current_view_name': current_view_name,
        'current_app': current_app,
    }
    return {
        'integrated_nav': integrated_nav_items(**kwargs),
        'nav_groups': integrated_nav_groups(**kwargs),
        'admin_nav_menu_label': ADMIN_NAV_MENU_LABEL,
        'admin_nav_items': admin_nav_items(user=request.user)
        if request.user.is_authenticated
        else [],
    }


def page_meta(request):
    return {'page_meta': resolve_page_meta(request)}


def input_limits(request):
    return {
        'limits': {
            'title': il.TITLE_MAX_LENGTH,
            'description': il.DESCRIPTION_MAX_LENGTH,
            'step_description': il.STEP_DESCRIPTION_MAX_LENGTH,
            'body': il.BODY_TEXT_MAX_LENGTH,
            'long_text': il.LONG_TEXT_MAX_LENGTH,
            'short_label': il.SHORT_LABEL_MAX_LENGTH,
            'search': il.SEARCH_QUERY_MAX_LENGTH,
        },
    }
