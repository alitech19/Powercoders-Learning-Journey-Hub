from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BugReportCreateForm, BugReportReplyForm
from .models import BugReport
from .permissions import admin_inbox_required, module_enabled_required
from .services import (
    BugReportWorkflowError,
    add_staff_reply,
    close_report,
    create_report,
    reject_report,
    reopen_report,
    take_report,
)
from .url_utils import normalize_page_url


@module_enabled_required
def report_create(request):
    page_url, page_path = normalize_page_url(request, request.GET.get('from', ''))
    if request.method == 'POST':
        form = BugReportCreateForm(request.POST)
        if form.is_valid():
            create_report(
                reporter=request.user,
                page_url=page_url,
                page_path=page_path,
                description=form.cleaned_data['description'],
            )
            messages.success(request, 'Thanks — we’ll review your report.')
            return redirect('dashboard:dashboard')
    else:
        form = BugReportCreateForm()

    return render(
        request,
        'bug_reports/report_create.html',
        {
            'form': form,
            'page_url': page_url,
        },
    )


@admin_inbox_required
def report_list(request):
    qs = BugReport.objects.select_related('reporter', 'assigned_to').order_by('-created_at')

    status = request.GET.get('status', '').strip()
    if status in BugReport.Status.values:
        qs = qs.filter(status=status)

    assigned = request.GET.get('assigned', '').strip()
    if assigned == 'me':
        qs = qs.filter(assigned_to=request.user)
    elif assigned == 'unassigned':
        qs = qs.filter(assigned_to__isnull=True)
    elif assigned == 'open':
        qs = qs.filter(
            status__in=[
                BugReport.Status.SUBMITTED,
                BugReport.Status.IN_PROGRESS,
                BugReport.Status.REOPENED,
            ]
        )

    return render(
        request,
        'bug_reports/report_list.html',
        {
            'reports': qs[:200],
            'status_filter': status,
            'assigned_filter': assigned,
            'status_choices': BugReport.Status.choices,
        },
    )


@admin_inbox_required
def report_detail(request, pk):
    report = get_object_or_404(
        BugReport.objects.select_related('reporter', 'assigned_to', 'reporter__cohort', 'reporter__group'),
        pk=pk,
    )
    reply_form = BugReportReplyForm()
    return render(
        request,
        'bug_reports/report_detail.html',
        {
            'report': report,
            'messages_thread': report.messages.select_related('author'),
            'reply_form': reply_form,
            'can_take': report.status in (BugReport.Status.SUBMITTED, BugReport.Status.REOPENED)
            and (report.assigned_to_id is None or report.assigned_to_id == request.user.pk),
        },
    )


def _redirect_detail(pk):
    return redirect('bug_reports:report_detail', pk=pk)


@admin_inbox_required
@require_POST
def report_take(request, pk):
    report = get_object_or_404(BugReport, pk=pk)
    try:
        take_report(report=report, admin_user=request.user)
        messages.success(request, 'Report marked in progress.')
    except BugReportWorkflowError as exc:
        messages.error(request, str(exc))
    return _redirect_detail(pk)


@admin_inbox_required
@require_POST
def report_close(request, pk):
    report = get_object_or_404(BugReport, pk=pk)
    close_report(report=report)
    messages.success(request, 'Report closed.')
    return _redirect_detail(pk)


@admin_inbox_required
@require_POST
def report_reject(request, pk):
    report = get_object_or_404(BugReport, pk=pk)
    reject_report(report=report)
    messages.success(request, 'Report rejected.')
    return _redirect_detail(pk)


@admin_inbox_required
@require_POST
def report_reopen(request, pk):
    report = get_object_or_404(BugReport, pk=pk)
    try:
        reopen_report(report=report)
        messages.success(request, 'Report reopened.')
    except BugReportWorkflowError as exc:
        messages.error(request, str(exc))
    return _redirect_detail(pk)


@admin_inbox_required
@require_POST
def report_reply(request, pk):
    report = get_object_or_404(BugReport, pk=pk)
    form = BugReportReplyForm(request.POST)
    if form.is_valid():
        add_staff_reply(
            report=report,
            author=request.user,
            body=form.cleaned_data['body'],
        )
        messages.success(request, 'Reply sent to reporter.')
    else:
        messages.error(request, 'Reply cannot be empty.')
    return _redirect_detail(pk)
