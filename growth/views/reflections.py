from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import ReflectionForm
from ..models import WeeklyReflection
from ..selectors import get_visible_reflections_for_user
from ..services.permissions import (
    can_create_feedback,
    can_edit_reflection,
    can_view_reflection,
)
from tracker.permissions import user_is_student


def _get_reflection_or_404(user, pk):
    reflection = get_object_or_404(
        WeeklyReflection.objects.select_related('student'), pk=pk,
    )
    if not can_view_reflection(user, reflection):
        raise Http404
    return reflection


@login_required
def reflection_list(request):
    reflections = get_visible_reflections_for_user(request.user)
    context = {
        'reflections': reflections,
        'is_student': user_is_student(request.user),
    }
    return render(request, 'growth/reflections/reflection_list.html', context)


@login_required
def reflection_create(request):
    if not user_is_student(request.user):
        return redirect('growth:reflection_list')

    if request.method == 'POST':
        form = ReflectionForm(request.POST, student=request.user)
        if form.is_valid():
            reflection = form.save(commit=False)
            reflection.student = request.user
            reflection.save()
            messages.success(request, 'Reflection submitted.')
            return redirect('growth:reflection_detail', pk=reflection.pk)
    else:
        form = ReflectionForm(student=request.user)
    return render(request, 'growth/reflections/reflection_form.html', {
        'form': form,
        'title': 'New weekly reflection',
    })


@login_required
def reflection_detail(request, pk):
    reflection = _get_reflection_or_404(request.user, pk)
    feedback_list = reflection.feedback.select_related('author').all()

    context = {
        'reflection': reflection,
        'feedback_list': feedback_list,
        'can_edit': can_edit_reflection(request.user, reflection),
        'can_give_feedback': can_create_feedback(request.user, reflection),
    }
    return render(request, 'growth/reflections/reflection_detail.html', context)


@login_required
def reflection_edit(request, pk):
    reflection = _get_reflection_or_404(request.user, pk)
    if not can_edit_reflection(request.user, reflection):
        return HttpResponseForbidden('You cannot edit this reflection.')

    if request.method == 'POST':
        form = ReflectionForm(
            request.POST, instance=reflection, student=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Reflection updated.')
            return redirect('growth:reflection_detail', pk=reflection.pk)
    else:
        form = ReflectionForm(instance=reflection, student=request.user)
    return render(request, 'growth/reflections/reflection_form.html', {
        'form': form,
        'title': 'Edit reflection',
    })
