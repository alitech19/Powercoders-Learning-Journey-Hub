from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required

from .models import ProjectSpace, ProjectSpaceMembership
from .permissions import can_manage_project_space, get_listable_project_spaces
from .project_forms import ProjectMemberAddForm, ProjectSpaceForm
from .slack_forms import apply_slack_mapping_from_request, slack_mapping_context


@admin_required
def project_list(request):
    projects = list(get_listable_project_spaces(request.user).prefetch_related('memberships__user'))
    return render(request, 'group_space/project_list.html', {
        'projects': projects,
    })


@admin_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectSpaceForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            messages.success(request, f'Group space “{project.title}” created.')
            return redirect('group_space:project_detail', pk=project.pk)
    else:
        form = ProjectSpaceForm()
    return render(request, 'group_space/project_form.html', {
        'form': form,
        'form_title': 'New group space',
    })


@admin_required
def project_detail(request, pk):
    project = get_object_or_404(ProjectSpace.objects.prefetch_related('memberships__user'), pk=pk)
    if not can_manage_project_space(request.user, project):
        raise Http404

    if request.method == 'POST':
        form = ProjectSpaceForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            slack_error = apply_slack_mapping_from_request(request, project_space=project)
            if slack_error:
                messages.warning(request, f'Slack mapping not saved: {slack_error}')
            messages.success(request, 'Group space updated.')
            return redirect('group_space:project_detail', pk=project.pk)
    else:
        form = ProjectSpaceForm(instance=project)

    members = project.memberships.select_related('user').order_by('user__display_name')
    add_form = ProjectMemberAddForm(project_space=project)
    return render(request, 'group_space/project_detail.html', {
        'project': project,
        'form': form,
        'members': members,
        'add_form': add_form,
        'feed_url': f"{reverse('group_space:feed')}?kind=project&space={project.pk}",
        **slack_mapping_context(project_space=project),
    })


@admin_required
@require_POST
def project_member_add(request, pk):
    project = get_object_or_404(ProjectSpace, pk=pk)
    if not can_manage_project_space(request.user, project):
        raise Http404
    form = ProjectMemberAddForm(request.POST, project_space=project)
    if form.is_valid():
        user = form.cleaned_data['user_id']
        ProjectSpaceMembership.objects.create(
            project_space=project,
            user=user,
            role=form.membership_role,
            added_by=request.user,
        )
        messages.success(request, f'Added {user.display_name} to the group space.')
    else:
        messages.error(request, form.errors.get('user_id', ['Could not add member.'])[0])
    return redirect('group_space:project_detail', pk=project.pk)


@admin_required
@require_POST
def project_member_remove(request, pk, user_pk):
    project = get_object_or_404(ProjectSpace, pk=pk)
    if not can_manage_project_space(request.user, project):
        raise Http404
    membership = get_object_or_404(ProjectSpaceMembership, project_space=project, user_id=user_pk)
    membership.delete()
    messages.success(request, 'Member removed.')
    return redirect('group_space:project_detail', pk=project.pk)


@admin_required
@require_POST
def project_archive(request, pk):
    project = get_object_or_404(ProjectSpace, pk=pk)
    if not can_manage_project_space(request.user, project):
        raise Http404
    project.is_archived = True
    project.save(update_fields=['is_archived', 'updated_at'])
    messages.success(request, 'Group space archived (read-only).')
    return redirect('group_space:project_list')


@admin_required
@require_POST
def project_unarchive(request, pk):
    project = get_object_or_404(ProjectSpace, pk=pk)
    if not can_manage_project_space(request.user, project):
        raise Http404
    project.is_archived = False
    project.save(update_fields=['is_archived', 'updated_at'])
    messages.success(request, 'Group space restored.')
    return redirect('group_space:project_detail', pk=project.pk)
