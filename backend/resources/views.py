from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import User

from .forms import ResourceContainerForm, ResourceItemForm
from .models import ResourceContainer, ResourceItem
from .permissions import (
    can_create_personal_container,
    can_create_thematic_container,
    can_delete_container,
    can_edit_container_items,
    can_edit_container_metadata,
    get_container_or_404,
    get_item_or_404,
    resolve_selected_group,
)
from .services import next_item_sort_order


def _tab_url(tab, *, group=None):
    params = f'tab={tab}'
    if group:
        params += f'&group={group.pk}'
    return f"{reverse('resources:index')}?{params}"


def _container_return_url(container):
    if container.container_type == ResourceContainer.ContainerType.PERSONAL:
        return _tab_url('my')
    if container.container_type == ResourceContainer.ContainerType.GROUP:
        return _tab_url('group', group=container.group)
    if container.container_type == ResourceContainer.ContainerType.PROJECT:
        return _tab_url('project')
    return _tab_url('themes', group=container.group)


@login_required
def index(request):
    tab = request.GET.get('tab', 'my')
    if tab not in ('my', 'group', 'project', 'themes'):
        tab = 'my'

    selected_group, available_groups = resolve_selected_group(request.user, request.GET.get('group', ''))
    containers = []

    if tab == 'my':
        containers = list(
            ResourceContainer.objects.filter(
                container_type=ResourceContainer.ContainerType.PERSONAL,
                owner=request.user,
            )
        )
    elif tab == 'group':
        if available_groups:
            group_ids = [g.pk for g in available_groups]
            containers = list(
                ResourceContainer.objects.filter(
                    container_type=ResourceContainer.ContainerType.GROUP,
                    is_system=True,
                    group_id__in=group_ids,
                ).select_related('group__cohort')
            )
    elif tab == 'project':
        from group_space.permissions import get_accessible_project_spaces

        project_ids = [p.pk for p in get_accessible_project_spaces(request.user)]
        containers = list(
            ResourceContainer.objects.filter(
                container_type=ResourceContainer.ContainerType.PROJECT,
                is_system=True,
                project_space_id__in=project_ids,
            ).select_related('project_space')
        )
    elif tab == 'themes' and selected_group:
        containers = list(
            ResourceContainer.objects.filter(
                container_type=ResourceContainer.ContainerType.THEMATIC,
                group=selected_group,
            )
        )

    can_create_personal = can_create_personal_container(request.user)
    can_create_thematic = bool(
        selected_group and can_create_thematic_container(request.user, selected_group),
    )
    create_url = None
    create_label = None
    if tab == 'my' and can_create_personal:
        create_url = f"{reverse('resources:container_create')}?tab=my"
        create_label = 'New list'
    elif tab == 'themes' and can_create_thematic:
        create_url = f"{reverse('resources:container_create')}?tab=themes&group={selected_group.pk}"
        create_label = 'New theme'

    return render(request, 'resources/index.html', {
        'tab': tab,
        'containers': containers,
        'selected_group': selected_group,
        'available_groups': available_groups,
        'can_create_personal': can_create_personal,
        'can_create_thematic': can_create_thematic,
        'create_url': create_url,
        'create_label': create_label,
    })


@login_required
def container_detail(request, pk):
    container = get_container_or_404(request.user, pk)
    items = container.items.select_related('source_post', 'created_by')
    return render(request, 'resources/container_detail.html', {
        'container': container,
        'items': items,
        'can_edit': can_edit_container_items(request.user, container),
        'can_edit_meta': can_edit_container_metadata(request.user, container),
        'can_delete_container': can_delete_container(request.user, container),
        'return_url': _container_return_url(container),
    })


@login_required
def container_create(request):
    tab = request.GET.get('tab', 'my')
    selected_group, available_groups = resolve_selected_group(request.user, request.GET.get('group', ''))

    if tab == 'themes':
        if not selected_group or not can_create_thematic_container(request.user, selected_group):
            raise Http404
        container_type = ResourceContainer.ContainerType.THEMATIC
        title_default = ''
    else:
        if not can_create_personal_container(request.user):
            raise Http404
        container_type = ResourceContainer.ContainerType.PERSONAL
        title_default = ''
        selected_group = None

    if request.method == 'POST':
        form = ResourceContainerForm(request.POST)
        if form.is_valid():
            container = form.save(commit=False)
            container.container_type = container_type
            container.created_by = request.user
            if container_type == ResourceContainer.ContainerType.PERSONAL:
                container.owner = request.user
            else:
                container.group = selected_group
            container.save()
            messages.success(request, 'Container created.')
            return redirect('resources:container_detail', pk=container.pk)
    else:
        form = ResourceContainerForm(initial={'title': title_default})

    return render(request, 'resources/container_form.html', {
        'form': form,
        'form_title': 'New theme' if tab == 'themes' else 'New personal list',
        'cancel_url': _tab_url(tab, group=selected_group),
    })


@login_required
def container_edit(request, pk):
    container = get_container_or_404(request.user, pk)
    if not can_edit_container_metadata(request.user, container):
        raise Http404

    if request.method == 'POST':
        form = ResourceContainerForm(request.POST, instance=container)
        if form.is_valid():
            form.save()
            messages.success(request, 'Container updated.')
            return redirect('resources:container_detail', pk=container.pk)
    else:
        form = ResourceContainerForm(instance=container)

    return render(request, 'resources/container_form.html', {
        'form': form,
        'form_title': 'Rename container',
        'cancel_url': reverse('resources:container_detail', kwargs={'pk': container.pk}),
    })


@login_required
def container_delete(request, pk):
    container = get_container_or_404(request.user, pk)
    if not can_delete_container(request.user, container):
        raise Http404
    return_url = _container_return_url(container)

    if request.method == 'POST':
        container.delete()
        messages.success(request, 'Container removed.')
        return redirect(return_url)

    return render(request, 'resources/container_confirm_delete.html', {
        'container': container,
        'return_url': return_url,
    })


@login_required
def item_create(request, container_pk):
    container = get_container_or_404(request.user, container_pk)
    if not can_edit_container_items(request.user, container):
        raise Http404

    if request.method == 'POST':
        form = ResourceItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.container = container
            item.created_by = request.user
            item.sort_order = next_item_sort_order(container)
            item.save()
            messages.success(request, 'Resource added.')
            return redirect('resources:container_detail', pk=container.pk)
    else:
        form = ResourceItemForm()

    return render(request, 'resources/item_form.html', {
        'form': form,
        'form_title': 'Add resource',
        'container': container,
        'cancel_url': reverse('resources:container_detail', kwargs={'pk': container.pk}),
    })


@login_required
def item_edit(request, pk):
    item = get_item_or_404(request.user, pk)
    if not can_edit_container_items(request.user, item.container):
        raise Http404

    if request.method == 'POST':
        form = ResourceItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Resource updated.')
            return redirect('resources:container_detail', pk=item.container_id)
    else:
        form = ResourceItemForm(instance=item)

    return render(request, 'resources/item_form.html', {
        'form': form,
        'form_title': 'Edit resource',
        'container': item.container,
        'cancel_url': reverse('resources:container_detail', kwargs={'pk': item.container_id}),
    })


@login_required
@require_POST
def item_delete(request, pk):
    item = get_item_or_404(request.user, pk)
    if not can_edit_container_items(request.user, item.container):
        raise Http404
    container_pk = item.container_id
    item.delete()
    messages.success(request, 'Resource removed.')
    return redirect('resources:container_detail', pk=container_pk)


@login_required
@require_POST
def item_move(request, pk):
    item = get_item_or_404(request.user, pk)
    if not can_edit_container_items(request.user, item.container):
        raise Http404
    direction = request.POST.get('direction')
    siblings = list(item.container.items.order_by('sort_order', 'pk'))
    idx = next(i for i, row in enumerate(siblings) if row.pk == item.pk)
    if direction == 'up' and idx > 0:
        prev = siblings[idx - 1]
        item.sort_order, prev.sort_order = prev.sort_order, item.sort_order
        item.save(update_fields=['sort_order', 'updated_at'])
        prev.save(update_fields=['sort_order', 'updated_at'])
    elif direction == 'down' and idx < len(siblings) - 1:
        nxt = siblings[idx + 1]
        item.sort_order, nxt.sort_order = nxt.sort_order, item.sort_order
        item.save(update_fields=['sort_order', 'updated_at'])
        nxt.save(update_fields=['sort_order', 'updated_at'])
    return redirect('resources:container_detail', pk=item.container_id)
