from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import DailyJournalEntryForm
from ..models import DailyJournalEntry
from ..selectors import get_visible_journal_entries_for_user
from ..services.permissions import (
    can_create_feedback,
    can_edit_journal_entry,
    can_view_journal_entry,
)
from tracker.permissions import user_is_student


def _get_entry_or_404(user, pk):
    entry = get_object_or_404(
        DailyJournalEntry.objects.select_related('student'), pk=pk,
    )
    if not can_view_journal_entry(user, entry):
        raise Http404
    return entry


@login_required
def journal_list(request):
    entries = get_visible_journal_entries_for_user(request.user)
    context = {
        'entries': entries,
        'is_student': user_is_student(request.user),
    }
    return render(request, 'growth/journal/journal_list.html', context)


@login_required
def journal_create(request):
    if not user_is_student(request.user):
        return redirect('growth:journal_list')

    if request.method == 'POST':
        form = DailyJournalEntryForm(request.POST, student=request.user)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.student = request.user
            entry.save()
            messages.success(request, 'Journal entry saved.')
            return redirect('growth:journal_detail', pk=entry.pk)
    else:
        form = DailyJournalEntryForm(student=request.user)
    return render(request, 'growth/journal/journal_form.html', {
        'form': form,
        'title': 'New journal entry',
    })


@login_required
def journal_detail(request, pk):
    entry = _get_entry_or_404(request.user, pk)
    feedback_list = entry.feedback.select_related('author').all()

    context = {
        'entry': entry,
        'feedback_list': feedback_list,
        'can_edit': can_edit_journal_entry(request.user, entry),
        'can_give_feedback': can_create_feedback(request.user, entry),
    }
    return render(request, 'growth/journal/journal_detail.html', context)


@login_required
def journal_edit(request, pk):
    entry = _get_entry_or_404(request.user, pk)
    if not can_edit_journal_entry(request.user, entry):
        return HttpResponseForbidden('You cannot edit this journal entry.')

    if request.method == 'POST':
        form = DailyJournalEntryForm(
            request.POST, instance=entry, student=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Journal entry updated.')
            return redirect('growth:journal_detail', pk=entry.pk)
    else:
        form = DailyJournalEntryForm(instance=entry, student=request.user)
    return render(request, 'growth/journal/journal_form.html', {
        'form': form,
        'title': 'Edit journal entry',
    })
