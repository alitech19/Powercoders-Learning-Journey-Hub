"""Per-model hooks for generic feedback permissions and template context."""


class FeedbackHandlers:
    def __init__(self, *, can_view, can_add, extra_context=None, section_template='feedback/_section.html'):
        self.can_view = can_view
        self.can_add = can_add
        self.extra_context = extra_context or (lambda target, viewer: {})
        self.section_template = section_template


_handlers = {}


def register(model, handlers):
    _handlers[model._meta.label_lower] = handlers


def get_handlers(obj):
    return _handlers.get(obj._meta.label_lower)
