from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import FeedbackForm
from ..models import DailyJournalEntry, Goal, WeeklyReflection
from ..services.permissions import can_create_feedback

MODEL_MAP = {
    'goal': Goal,
    'reflection': WeeklyReflection,
    'journal': DailyJournalEntry,
}

REDIRECT_MAP = {
    Goal: 'growth:goal_detail',
    WeeklyReflection: 'growth:reflection_detail',
    DailyJournalEntry: 'growth:journal_detail',
}


def _resolve_target(content_type_label, object_id):
    """Look up the target object from a URL-friendly content-type label."""
    model_class = MODEL_MAP.get(content_type_label)
    if model_class is None:
        raise Http404
    ct = ContentType.objects.get_for_model(model_class)
    target = get_object_or_404(model_class.objects.select_related('student'), pk=object_id)
    return ct, target


@login_required
def feedback_create(request, content_type, object_id):
    ct, target = _resolve_target(content_type, object_id)

    if not can_create_feedback(request.user, target):
        return HttpResponseForbidden('You cannot leave feedback here.')

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.author = request.user
            fb.student = target.student
            fb.content_type = ct
            fb.object_id = target.pk
            fb.save()
            messages.success(request, 'Feedback submitted.')

            redirect_name = REDIRECT_MAP.get(type(target))
            if redirect_name:
                return redirect(redirect_name, pk=target.pk)
            return redirect('growth:goal_list')
    else:
        form = FeedbackForm()

    return render(request, 'growth/feedback/feedback_form.html', {
        'form': form,
        'target': target,
        'content_type_label': content_type,
    })
