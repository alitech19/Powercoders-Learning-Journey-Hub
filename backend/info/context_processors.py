from .registry import resolve_page_help


def page_help(request):
    return {'page_help': resolve_page_help(request)}