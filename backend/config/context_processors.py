from .nav import integrated_nav_items
from config import input_limits as il


def integrated_nav(request):
    resolver = getattr(request, 'resolver_match', None)
    current_view_name = resolver.view_name if resolver else None
    return {'integrated_nav': integrated_nav_items(current_view_name=current_view_name)}


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
