from django.contrib import messages
from django.contrib.auth.decorators import login_required
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

from feedback.services import build_section_context

from .constants import (
    MOOD_OPTIONS,
    SEARCH_QUERY_MAX_LENGTH,
    TAG_CHOICES,
    TAG_CUSTOM,
    TAG_PROJECT,
    TAG_WEEKLY,
    WELLBEING_DIMENSIONS,
)
from .forms import ReflectionForm, wellbeing_form_context
from .models import Reflection
from .permissions import (
    can_create_reflections,
    can_delete_reflection,
    can_edit_reflection,
    can_view_reflection,
    filter_reflections_queryset,
    get_visible_reflections_for_user,
    order_reflections_newest_first,
)


def _get_reflection_or_404(user, pk):
    reflection = get_object_or_404(
        Reflection.objects.select_related('author', 'author__group'),
        pk=pk,
    )
    if not can_view_reflection(user, reflection):
        raise Http404
    return reflection


def _list_query_params(request):
    return {
        'tag_filter': request.GET.get('tag', ''),
        'search_query': request.GET.get('q', '').strip()[:SEARCH_QUERY_MAX_LENGTH],
        'student_filter': request.GET.get('student', ''),
    }


def _apply_list_filters(qs, *, tag_filter, search_query, student_filter):
    tag = tag_filter if tag_filter in (TAG_WEEKLY, TAG_PROJECT, TAG_CUSTOM) else None
    student_id = student_filter if student_filter.isdigit() else None
    return filter_reflections_queryset(
        qs,
        tag=tag,
        search=search_query or None,
        student_id=student_id,
    )


@login_required
def reflection_list(request):
    user = request.user
    params = _list_query_params(request)
    qs = get_visible_reflections_for_user(user)
    qs = _apply_list_filters(
        qs,
        tag_filter=params['tag_filter'],
        search_query=params['search_query'],
        student_filter=params['student_filter'],
    )
    qs = order_reflections_newest_first(qs)

    if user_is_student(user):
        all_own = get_visible_reflections_for_user(user)
        context = {
            'view_as': 'student',
            'total': all_own.count(),
            'weekly_tag_count': all_own.filter(tags__contains=[TAG_WEEKLY]).count(),
            'project_tag_count': all_own.filter(tags__contains=[TAG_PROJECT]).count(),
            'can_create': can_create_reflections(user),
            'students': None,
            'filtered_student': None,
        }
    else:
        if user_is_admin(user):
            students = User.objects.filter(
                role=User.Role.STUDENT, is_active=True,
            ).order_by('display_name')
        else:
            students = get_teacher_accessible_students(user)
        filtered_student = None
        if params['student_filter']:
            filtered_student = students.filter(pk=params['student_filter']).first()
        context = {
            'view_as': 'admin' if user_is_admin(user) else 'teacher',
            'students': students,
            'filtered_student': filtered_student,
            'can_create': False,
        }

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context.update({
        'reflections': page_obj,
        'page_obj': page_obj,
        'tag_filter': params['tag_filter'],
        'search_query': params['search_query'],
        'student_filter': params['student_filter'],
        'tag_choices': TAG_CHOICES,
        'search_max_length': SEARCH_QUERY_MAX_LENGTH,
    })
    return render(request, 'reflections/list.html', context)


@login_required
def reflection_create(request):
    if not can_create_reflections(request.user):
        return redirect('reflections:list')

    if request.method == 'POST':
        form = ReflectionForm(request.POST, creating=True)
        if form.is_valid():
            reflection = form.save(commit=False)
            reflection.author = request.user
            reflection.save()
            messages.success(request, 'Reflection created.')
            return redirect('reflections:detail', pk=reflection.pk)
    else:
        form = ReflectionForm(creating=True)

    return render(request, 'reflections/form.html', {
        'form': form,
        'action': 'create',
        **wellbeing_form_context(form),
    })


def _wellbeing_rows(reflection):
    if not reflection.show_wellbeing:
        return []
    emoji_map = {level: emoji for level, emoji, _label in MOOD_OPTIONS}
    rows = []
    for field_name, label, _hint in WELLBEING_DIMENSIONS:
        value = getattr(reflection, field_name, '')
        rows.append({
            'label': label,
            'emoji': emoji_map.get(value, '') if value else '',
            'filled': bool(value),
        })
    return rows


@login_required
def reflection_detail(request, pk):
    reflection = _get_reflection_or_404(request.user, pk)
    user = request.user
    is_staff_view = user.pk != reflection.author_id and (
        user_is_teacher(user) or user_is_admin(user)
    )
    ctx = {
        'reflection': reflection,
        'wellbeing_rows': _wellbeing_rows(reflection),
        'can_edit': can_edit_reflection(user, reflection),
        'can_delete': can_delete_reflection(user, reflection),
        'is_staff_view': is_staff_view,
    }
    feedback_ctx = build_section_context(target=reflection, viewer=user)
    if feedback_ctx:
        ctx.update(feedback_ctx)
        ctx['show_feedback'] = True
    else:
        ctx['show_feedback'] = False
    return render(request, 'reflections/detail.html', ctx)


@login_required
def reflection_edit(request, pk):
    reflection = _get_reflection_or_404(request.user, pk)
    if not can_edit_reflection(request.user, reflection):
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = ReflectionForm(request.POST, instance=reflection)
        if form.is_valid():
            form.save()
            messages.success(request, 'Reflection updated.')
            return redirect('reflections:detail', pk=reflection.pk)
    else:
        form = ReflectionForm(instance=reflection)

    return render(request, 'reflections/form.html', {
        'form': form,
        'action': 'edit',
        'reflection': reflection,
        **wellbeing_form_context(form),
    })


@login_required
def reflection_delete(request, pk):
    reflection = _get_reflection_or_404(request.user, pk)
    if not can_delete_reflection(request.user, reflection):
        return HttpResponseForbidden()
    if request.method == 'POST':
        reflection.delete()
        messages.success(request, 'Reflection deleted.')
        return redirect('reflections:list')
    return render(request, 'reflections/confirm_delete.html', {'reflection': reflection})
