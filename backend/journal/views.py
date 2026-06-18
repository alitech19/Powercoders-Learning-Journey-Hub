from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from cohorts.permissions import (
    get_teacher_accessible_students,
    user_is_admin,
    user_is_student,
    user_is_teacher,
)

from config.input_limits import SEARCH_QUERY_MAX_LENGTH
from feedback.services import build_section_context

from .constants import MOOD_OPTIONS
from .forms import JournalEntryForm
from .models import JournalEntry
from .permissions import (
    can_create_journal_entries,
    can_delete_journal_entry,
    can_edit_journal_entry,
    can_view_journal_entry,
    filter_journal_entries_queryset,
    get_visible_journal_entries_for_user,
    order_journal_entries_newest_first,
)
from .services import writing_streak


def _get_entry_or_404(user, pk):
    entry = get_object_or_404(
        JournalEntry.objects.select_related('author', 'author__group'),
        pk=pk,
    )
    if not can_view_journal_entry(user, entry):
        raise PermissionDenied
    return entry


def _list_query_params(request):
    return {
        'tag_filter': request.GET.get('tag', '').strip()[:SEARCH_QUERY_MAX_LENGTH],
        'search_query': request.GET.get('q', '').strip()[:SEARCH_QUERY_MAX_LENGTH],
        'student_filter': request.GET.get('student', ''),
    }


@login_required
def entry_list(request):
    user = request.user
    params = _list_query_params(request)
    qs = get_visible_journal_entries_for_user(user)
    qs = filter_journal_entries_queryset(
        qs,
        tag=params['tag_filter'] or None,
        search=params['search_query'] or None,
        student_id=params['student_filter'] if params['student_filter'].isdigit() else None,
    )
    qs = order_journal_entries_newest_first(qs)

    from datetime import date, timedelta

    week_start = date.today() - timedelta(days=date.today().weekday())

    if user_is_student(user):
        all_own = get_visible_journal_entries_for_user(user)
        context = {
            'view_as': 'student',
            'total': all_own.count(),
            'this_week': all_own.filter(entry_date__gte=week_start).count(),
            'streak': writing_streak(user),
            'can_create': can_create_journal_entries(user),
            'students': None,
        }
    else:
        if user_is_admin(user):
            students = User.objects.filter(
                role=User.Role.STUDENT, is_active=True,
            ).order_by('display_name')
        else:
            students = get_teacher_accessible_students(user)
        context = {
            'view_as': 'admin' if user_is_admin(user) else 'teacher',
            'students': students,
            'can_create': False,
        }

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context.update({
        'entries': page_obj,
        'page_obj': page_obj,
        'tag_filter': params['tag_filter'],
        'search_query': params['search_query'],
        'student_filter': params['student_filter'],
        'mood_options': MOOD_OPTIONS,
    })
    return render(request, 'journal/entry_list.html', context)


@login_required
def entry_create(request):
    if not can_create_journal_entries(request.user):
        return redirect('journal:list')

    if request.method == 'POST':
        form = JournalEntryForm(request.POST, creating=True)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.author = request.user
            entry.save()
            messages.success(request, 'Journal entry created.')
            return redirect('journal:detail', pk=entry.pk)
    else:
        form = JournalEntryForm(creating=True)

    return render(request, 'journal/entry_form.html', {
        'form': form,
        'action': 'create',
        'mood_options': MOOD_OPTIONS,
    })


@login_required
def entry_detail(request, pk):
    entry = _get_entry_or_404(request.user, pk)
    user = request.user
    is_staff_view = user.pk != entry.author_id and (
        user_is_teacher(user) or user_is_admin(user)
    )
    ctx = {
        'entry': entry,
        'can_edit': can_edit_journal_entry(user, entry),
        'can_delete': can_delete_journal_entry(user, entry),
        'is_staff_view': is_staff_view,
        'admin_delete': user_is_admin(user) and entry.author_id != user.pk,
    }
    feedback_ctx = build_section_context(target=entry, viewer=user)
    if feedback_ctx:
        ctx.update(feedback_ctx)
        ctx['show_feedback'] = True
    else:
        ctx['show_feedback'] = False
    return render(request, 'journal/entry_detail.html', ctx)


@login_required
def entry_edit(request, pk):
    entry = _get_entry_or_404(request.user, pk)
    if not can_edit_journal_entry(request.user, entry):
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = JournalEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, 'Journal entry updated.')
            return redirect('journal:detail', pk=entry.pk)
    else:
        form = JournalEntryForm(instance=entry)

    return render(request, 'journal/entry_form.html', {
        'form': form,
        'action': 'edit',
        'entry': entry,
        'mood_options': MOOD_OPTIONS,
    })


@login_required
def entry_delete(request, pk):
    entry = _get_entry_or_404(request.user, pk)
    if not can_delete_journal_entry(request.user, entry):
        return HttpResponseForbidden()
    admin_delete = user_is_admin(request.user) and entry.author_id != request.user.pk
    if request.method == 'POST':
        entry.delete()
        messages.success(
            request,
            'Shared entry removed.' if admin_delete else 'Journal entry deleted.',
        )
        return redirect('journal:list')
    return render(request, 'journal/entry_confirm_delete.html', {
        'entry': entry,
        'admin_delete': admin_delete,
    })
