from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from django.contrib.auth.decorators import login_required

from .models import FeedbackEntry
from .registry import get_handlers
from .services import build_section_context, can_delete_entry, create_entry


def _get_target_or_404(content_type_id, object_id):
    ct = get_object_or_404(ContentType, pk=content_type_id)
    model = ct.model_class()
    if model is None:
        raise Http404
    return get_object_or_404(model, pk=object_id)


@login_required
@require_POST
def feedback_add(request, content_type_id, object_id):
    target = _get_target_or_404(content_type_id, object_id)
    handlers = get_handlers(target)
    if not handlers or not handlers.can_add(request.user, target):
        return HttpResponseForbidden()

    body = request.POST.get('body', '').strip()
    if body:
        create_entry(target=target, author=request.user, body=body)

    ctx = build_section_context(target=target, viewer=request.user)
    return render(request, handlers.section_template, ctx)


@login_required
@require_POST
def feedback_delete(request, pk):
    entry = get_object_or_404(FeedbackEntry.objects.select_related('content_type'), pk=pk)
    target = entry.content_object
    if target is None:
        raise Http404

    handlers = get_handlers(target)
    if not handlers or not handlers.can_view(request.user, target):
        return HttpResponseForbidden()
    if not can_delete_entry(request.user, entry):
        return HttpResponseForbidden()

    entry.delete()
    ctx = build_section_context(target=target, viewer=request.user)
    return render(request, handlers.section_template, ctx)
