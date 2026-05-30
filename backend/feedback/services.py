from django.contrib.contenttypes.models import ContentType

from cohorts.permissions import user_is_admin

from .models import FeedbackEntry
from .registry import get_handlers


def get_entries_for(target):
    ct = ContentType.objects.get_for_model(target)
    return (
        FeedbackEntry.objects.filter(content_type=ct, object_id=target.pk)
        .select_related('author')
        .order_by('created_at')
    )


def create_entry(*, target, author, body):
    ct = ContentType.objects.get_for_model(target)
    return FeedbackEntry.objects.create(
        content_type=ct,
        object_id=target.pk,
        author=author,
        body=body,
    )


def can_delete_entry(user, entry):
    if not user.is_authenticated:
        return False
    if user_is_admin(user):
        return True
    return entry.author_id == user.pk


def build_section_context(*, target, viewer):
    handlers = get_handlers(target)
    if not handlers or not handlers.can_view(viewer, target):
        return None

    ct = ContentType.objects.get_for_model(target)
    ctx = {
        'panel_id': f'{ct.model}-{target.pk}',
        'content_type_id': ct.pk,
        'object_id': target.pk,
        'entries': list(get_entries_for(target)),
        'can_add_feedback': handlers.can_add(viewer, target),
    }
    ctx.update(handlers.extra_context(target, viewer))
    return ctx


def render_section(*, request, target):
    ctx = build_section_context(target=target, viewer=request.user)
    if ctx is None:
        return None
    handlers = get_handlers(target)
    return handlers.section_template, ctx
