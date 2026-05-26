from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import WellbeingCheckInForm
from ..models import WellbeingCheckIn
from ..selectors import get_visible_wellbeing_checkins_for_user
from ..services.permissions import (
    can_create_feedback,
    can_edit_wellbeing_checkin,
    can_view_wellbeing_checkin,
)
from tracker.permissions import user_is_student


def _get_checkin_or_404(user, pk):
    checkin = get_object_or_404(
        WellbeingCheckIn.objects.select_related('student'), pk=pk,
    )
    if not can_view_wellbeing_checkin(user, checkin):
        raise Http404
    return checkin


@login_required
def wellbeing_list(request):
    checkins = get_visible_wellbeing_checkins_for_user(request.user)
    context = {
        'checkins': checkins,
        'is_student': user_is_student(request.user),
    }
    return render(request, 'growth/wellbeing/wellbeing_list.html', context)


@login_required
def wellbeing_create(request):
    if not user_is_student(request.user):
        return redirect('growth:wellbeing_list')

    if request.method == 'POST':
        form = WellbeingCheckInForm(request.POST, student=request.user)
        if form.is_valid():
            checkin = form.save(commit=False)
            checkin.student = request.user
            checkin.save()
            messages.success(request, 'Wellbeing check-in saved.')
            return redirect('growth:wellbeing_detail', pk=checkin.pk)
    else:
        form = WellbeingCheckInForm(student=request.user)
    return render(request, 'growth/wellbeing/wellbeing_form.html', {
        'form': form,
        'title': 'New wellbeing check-in',
    })


@login_required
def wellbeing_detail(request, pk):
    checkin = _get_checkin_or_404(request.user, pk)
    feedback_list = checkin.feedback.select_related('author').all()

    context = {
        'checkin': checkin,
        'feedback_list': feedback_list,
        'can_edit': can_edit_wellbeing_checkin(request.user, checkin),
        'can_give_feedback': can_create_feedback(request.user, checkin),
    }
    return render(request, 'growth/wellbeing/wellbeing_detail.html', context)


@login_required
def wellbeing_edit(request, pk):
    checkin = _get_checkin_or_404(request.user, pk)
    if not can_edit_wellbeing_checkin(request.user, checkin):
        return HttpResponseForbidden('You cannot edit this wellbeing check-in.')

    if request.method == 'POST':
        form = WellbeingCheckInForm(
            request.POST, instance=checkin, student=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Wellbeing check-in updated.')
            return redirect('growth:wellbeing_detail', pk=checkin.pk)
    else:
        form = WellbeingCheckInForm(instance=checkin, student=request.user)
    return render(request, 'growth/wellbeing/wellbeing_form.html', {
        'form': form,
        'title': 'Edit wellbeing check-in',
    })
