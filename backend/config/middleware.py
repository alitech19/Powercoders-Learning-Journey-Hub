from .module_access import is_module_enabled
from .modules import CORE_PREFIXES, slug_for_path
from .views import module_disabled_view


class ModuleGateMiddleware:
    """Return a friendly stub when a toggleable module is disabled."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path == '/' or any(path.startswith(prefix) for prefix in CORE_PREFIXES):
            return self.get_response(request)

        slug = slug_for_path(path)
        if slug and not is_module_enabled(slug):
            return module_disabled_view(request, slug)
        return self.get_response(request)
