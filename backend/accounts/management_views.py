"""Admin/teacher user, cohort, and student oversight views."""

import csv
import io

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from cohorts.models import Cohort, Group, GroupTeacher
from cohorts.permissions import get_teacher_group_ids, user_is_admin
from journal.models import JournalEntry
from reflections.models import Reflection
from tasks.models import TaskEnrollment

from .decorators import admin_required, teacher_or_admin_required
from .forms import CohortForm, CreateUserForm, GroupForm
from .student_oversight import (
    build_student_progress_rows,
    goal_enrollments_for_student,
    shared_habits_for_student,
    teacher_can_view_student,
    workflow_enrollments_for_student,
)

User = get_user_model()


# ── User management ───────────────────────────────────────────────────────────


@teacher_or_admin_required
def user_list(request):
    user = request.user
    role_filter = request.GET.get('role', '')
    search = request.GET.get('q', '').strip()

    if user_is_admin(user):
        qs = User.objects.select_related('cohort', 'group').order_by('role', 'display_name')
    else:
        group_ids = get_teacher_group_ids(user)
        qs = User.objects.filter(group_id__in=group_ids).select_related('cohort', 'group').order_by(
            'display_name'
        )

    if role_filter:
        qs = qs.filter(role=role_filter)
    if search:
        qs = qs.filter(Q(display_name__icontains=search) | Q(email__icontains=search))

    page_obj = Paginator(qs, 25).get_page(request.GET.get('page'))
    return render(
        request,
        'accounts/user_list.html',
        {
            'users': page_obj,
            'page_obj': page_obj,
            'role_filter': role_filter,
            'search': search,
            'is_admin': user_is_admin(user),
        },
    )


@teacher_or_admin_required
def user_create(request):
    user = request.user
    created_user = None
    temp_password = None

    if request.method == 'POST':
        form = CreateUserForm(request.POST, creator=user)
        if form.is_valid():
            email = form.cleaned_data['email']
            display_name = form.cleaned_data['display_name']
            role = form.cleaned_data.get('role') or User.Role.STUDENT
            cohort = form.cleaned_data.get('cohort')
            group = form.cleaned_data.get('group')
            if not cohort and group:
                cohort = group.cohort

            temp_password = CreateUserForm.generate_temp_password()
            created_user = User.objects.create_user(
                email=email,
                password=temp_password,
                display_name=display_name,
                role=role,
                cohort=cohort,
                group=group,
                must_change_password=True,
                is_staff=(role == User.Role.ADMIN),
                is_superuser=(role == User.Role.ADMIN),
            )
            from .emails import send_new_user_slack, send_welcome_email

            send_welcome_email(created_user, temp_password)
            send_new_user_slack(created_user)
            from accounts.notifications.staff_events import notify_new_user_account

            notify_new_user_account(created_user=created_user, created_by=request.user)
            messages.success(request, f'User {display_name} created. Share the temporary password securely.')
            form = CreateUserForm(creator=user)
    else:
        form = CreateUserForm(creator=user)

    return render(
        request,
        'accounts/user_create.html',
        {
            'form': form,
            'created_user': created_user,
            'temp_password': temp_password,
            'is_admin': user_is_admin(user),
        },
    )


@admin_required
def user_import(request):
    results = None
    if request.method == 'POST' and request.FILES.get('csv_file'):
        raw = request.FILES['csv_file'].read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(raw))
        created, skipped, errors = [], [], []

        for i, row in enumerate(reader, start=2):
            email = (row.get('email') or '').strip().lower()
            display_name = (row.get('display_name') or '').strip()
            role = (row.get('role') or 'student').strip().lower()
            cohort_name = (row.get('cohort') or '').strip()
            group_name = (row.get('group') or '').strip()

            if not email or not display_name:
                errors.append({'row': i, 'email': email, 'reason': 'Missing email or display_name'})
                continue

            if User.objects.filter(email=email).exists():
                skipped.append({'row': i, 'email': email, 'reason': 'Email already exists'})
                continue

            if role not in dict(User.Role.choices):
                role = User.Role.STUDENT

            cohort = Cohort.objects.filter(name__iexact=cohort_name).first() if cohort_name else None
            group = None
            if group_name:
                group_qs = Group.objects.filter(name__iexact=group_name)
                if cohort:
                    group_qs = group_qs.filter(cohort=cohort)
                group = group_qs.first()
                if group and not cohort:
                    cohort = group.cohort

            temp_pw = CreateUserForm.generate_temp_password()
            new_user = User.objects.create_user(
                email=email,
                password=temp_pw,
                display_name=display_name,
                role=role,
                cohort=cohort,
                group=group,
                must_change_password=True,
                is_staff=(role == User.Role.ADMIN),
                is_superuser=(role == User.Role.ADMIN),
            )
            from .emails import send_new_user_slack, send_welcome_email

            send_welcome_email(new_user, temp_pw)
            send_new_user_slack(new_user)
            from accounts.notifications.staff_events import notify_new_user_account

            notify_new_user_account(created_user=new_user, created_by=request.user)
            created.append(
                {
                    'row': i,
                    'email': email,
                    'display_name': display_name,
                    'temp_password': temp_pw,
                }
            )

        results = {'created': created, 'skipped': skipped, 'errors': errors}
        messages.success(request, f'Import finished: {len(created)} created.')

    return render(request, 'accounts/user_import.html', {'results': results})


@admin_required
def user_deactivate(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:user_list')
    if request.method == 'POST':
        target.is_active = False
        target.save(update_fields=['is_active'])
        messages.success(request, f'{target.display_name} has been deactivated.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_confirm_deactivate.html', {'target': target})


@admin_required
def user_reactivate(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        target.is_active = True
        target.save(update_fields=['is_active'])
        messages.success(request, f'{target.display_name} has been reactivated.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_confirm_reactivate.html', {'target': target})


@admin_required
def user_delete_account(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('accounts:user_list')
    if request.method == 'POST':
        name = target.display_name
        target.delete()
        messages.success(request, f'{name} and all their data have been permanently deleted.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_confirm_delete_account.html', {'target': target})


# ── Student oversight ─────────────────────────────────────────────────────────


@teacher_or_admin_required
def student_progress(request):
    user = request.user

    if user.role == User.Role.TEACHER:
        group_ids = get_teacher_group_ids(user)
        available_groups = Group.objects.filter(pk__in=group_ids).select_related('cohort').order_by(
            'cohort__name', 'name'
        )
        students_qs = User.objects.filter(role=User.Role.STUDENT, group_id__in=group_ids)
    else:
        available_groups = Group.objects.select_related('cohort').order_by('cohort__name', 'name')
        students_qs = User.objects.filter(role=User.Role.STUDENT)

    group_filter = request.GET.get('group', '')
    if group_filter:
        students_qs = students_qs.filter(group_id=group_filter)

    missing_filter = request.GET.get('filter', '') == 'missing_reflection'
    all_rows = build_student_progress_rows(students_qs, missing_filter=missing_filter)
    page_obj = Paginator(all_rows, 20).get_page(request.GET.get('page'))

    return render(
        request,
        'accounts/student_progress.html',
        {
            'student_rows': page_obj,
            'page_obj': page_obj,
            'available_groups': available_groups,
            'group_filter': group_filter,
            'missing_filter': missing_filter,
        },
    )


@teacher_or_admin_required
def student_detail(request, pk):
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    if not teacher_can_view_student(request.user, student):
        return redirect('accounts:student_progress')

    tab = request.GET.get('tab', 'workflows')
    workflow_enrollments = workflow_enrollments_for_student(student)
    goal_enrollments = goal_enrollments_for_student(student)
    task_enrollments = (
        TaskEnrollment.objects.filter(student=student)
        .select_related('task')
        .order_by('-task__updated_at')[:15]
    )
    reflections = (
        Reflection.objects.filter(author=student, visibility=Reflection.Visibility.SHARED)
        .order_by('-final_reflection_at', '-created_at')[:15]
    )
    journal_entries = (
        JournalEntry.objects.filter(author=student, visibility=JournalEntry.Visibility.SHARED)
        .order_by('-entry_date')[:15]
    )
    habits = shared_habits_for_student(student)

    return render(
        request,
        'accounts/student_detail.html',
        {
            'student': student,
            'tab': tab,
            'workflow_enrollments': workflow_enrollments,
            'goal_enrollments': goal_enrollments,
            'task_enrollments': task_enrollments,
            'reflections': reflections,
            'journal_entries': journal_entries,
            'habits': habits,
        },
    )


# ── Cohort / group management (admin) ─────────────────────────────────────────


def _save_group_teachers(group, teachers):
    GroupTeacher.objects.filter(group=group).delete()
    for teacher in teachers:
        GroupTeacher.objects.get_or_create(group=group, teacher=teacher)


@admin_required
def cohort_list(request):
    cohorts = (
        Cohort.objects.prefetch_related('groups')
        .annotate(group_count=Count('groups', distinct=True))
        .order_by('-start_date', 'name')
    )
    return render(request, 'accounts/cohort_list.html', {'cohorts': cohorts})


@admin_required
def cohort_create(request):
    if request.method == 'POST':
        form = CohortForm(request.POST)
        if form.is_valid():
            cohort = form.save()
            messages.success(request, f'Cohort "{cohort.name}" created.')
            return redirect('accounts:cohort_list')
    else:
        form = CohortForm()
    return render(request, 'accounts/cohort_form.html', {'form': form, 'title': 'New Cohort'})


@admin_required
def cohort_edit(request, pk):
    cohort = get_object_or_404(Cohort, pk=pk)
    if request.method == 'POST':
        form = CohortForm(request.POST, instance=cohort)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cohort "{cohort.name}" updated.')
            return redirect('accounts:cohort_list')
    else:
        form = CohortForm(instance=cohort)
    return render(
        request,
        'accounts/cohort_form.html',
        {'form': form, 'cohort': cohort, 'title': 'Edit Cohort'},
    )


@admin_required
def cohort_delete(request, pk):
    cohort = get_object_or_404(Cohort, pk=pk)
    if request.method == 'POST':
        name = cohort.name
        cohort.delete()
        messages.success(request, f'Cohort "{name}" deleted.')
        return redirect('accounts:cohort_list')
    return render(request, 'accounts/cohort_confirm_delete.html', {'cohort': cohort})


@admin_required
def group_create(request, cohort_pk):
    cohort = get_object_or_404(Cohort, pk=cohort_pk)
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            _save_group_teachers(group, form.cleaned_data.get('teachers', []))
            messages.success(request, f'Group "{group.name}" created.')
            return redirect('accounts:cohort_list')
    else:
        form = GroupForm(initial={'cohort': cohort})
    return render(
        request,
        'accounts/group_form.html',
        {'form': form, 'cohort': cohort, 'title': 'New Group'},
    )


@admin_required
def group_edit(request, pk):
    group = get_object_or_404(Group.objects.select_related('cohort'), pk=pk)
    from group_space.services import get_group_space_for_group
    from group_space.slack_forms import apply_slack_mapping_from_request, slack_mapping_context

    group_space = get_group_space_for_group(group)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            _save_group_teachers(group, form.cleaned_data.get('teachers', []))
            slack_error = apply_slack_mapping_from_request(request, group_space=group_space)
            if slack_error:
                messages.warning(request, f'Slack mapping not saved: {slack_error}')
            messages.success(request, f'Group "{group.name}" updated.')
            return redirect('accounts:cohort_list')
    else:
        form = GroupForm(instance=group)
    return render(
        request,
        'accounts/group_form.html',
        {
            'form': form,
            'group': group,
            'cohort': group.cohort,
            'title': 'Edit Group',
            **slack_mapping_context(group_space=group_space),
        },
    )


@admin_required
def group_delete(request, pk):
    group = get_object_or_404(Group.objects.select_related('cohort'), pk=pk)
    if request.method == 'POST':
        name = group.name
        group.delete()
        messages.success(request, f'Group "{name}" deleted.')
        return redirect('accounts:cohort_list')
    return render(request, 'accounts/group_confirm_delete.html', {'group': group})


@admin_required
def group_assign_students(request, pk):
    group = get_object_or_404(Group.objects.select_related('cohort'), pk=pk)
    students = (
        User.objects.filter(role=User.Role.STUDENT, cohort=group.cohort)
        .exclude(group=group)
        .order_by('display_name')
    )
    if request.method == 'POST':
        student_ids = request.POST.getlist('students')
        updated = User.objects.filter(pk__in=student_ids, cohort=group.cohort).update(group=group)
        messages.success(request, f'{updated} student(s) assigned to "{group.name}".')
        return redirect('accounts:cohort_list')
    return render(
        request,
        'accounts/group_assign_students.html',
        {'group': group, 'students': students},
    )
