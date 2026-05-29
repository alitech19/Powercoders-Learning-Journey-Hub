from .nav import integrated_nav_items


def integrated_nav(request):
    return {'integrated_nav': integrated_nav_items()}
