from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import User

from .chat import ChatItem, build_chat_timeline
from .forms import ChatComposerForm, PostForm
from .models import Post
from .permissions import (
    can_delete_post,
    can_edit_post,
    can_pin_post,
    can_post_in_group_space,
    get_accessible_groups,
    get_post_or_404,
)
from .constants import SHARE_KIND_PANEL
from .services import after_post_saved, get_group_space_for_group, resolve_group
from . import snapshots


def _share_menu_for(user):
    if user.role != User.Role.STUDENT:
        return None
    return snapshots.build_share_menu(user)


def _group_context(user, group, *, extra=None):
    ctx = {
        'group': group,
        'available_groups': get_accessible_groups(user),
        'selected_group_pk': str(group.pk) if group else '',
        'can_post': bool(group),
        'share_kind_panel': SHARE_KIND_PANEL,
    }
    if extra:
        ctx.update(extra)
    return ctx


def _feed_redirect(group):
    return redirect(f"{reverse('group_space:feed')}?group={group.pk}#chat-bottom")


def _bubble_response(request, post, group):
    item = ChatItem(kind='post', created_at=post.created_at, post=post)
    response = render(request, 'group_space/_chat_bubble.html', {
        'item': item,
        'user': request.user,
        'group': group,
    })
    response['HX-Trigger'] = 'chatScrollBottom, closeSharePanel'
    return response


@login_required
def feed(request):
    user = request.user
    available_groups = get_accessible_groups(user)
    group = resolve_group(available_groups, request.GET.get('group', ''))

    pinned_posts = []
    chat_items = []
    group_space = None
    share_menu = _share_menu_for(user)
    if group:
        group_space = get_group_space_for_group(group)
        pinned_posts, chat_items = build_chat_timeline(group_space)

    return render(request, 'group_space/feed.html', {
        **_group_context(user, group),
        'group_space': group_space,
        'pinned_posts': pinned_posts,
        'chat_items': chat_items,
        'share_menu': share_menu,
        'composer_form': ChatComposerForm(),
    })


@login_required
@require_POST
def message_create(request):
    user = request.user
    group = resolve_group(
        get_accessible_groups(user),
        request.POST.get('group_pk', ''),
    )
    if not group:
        raise Http404

    group_space = get_group_space_for_group(group)
    if not can_post_in_group_space(user, group_space):
        raise Http404

    form = ChatComposerForm(request.POST, request.FILES)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = user
        post.group_space = group_space
        post.save()
        after_post_saved(post)
        return _bubble_response(request, post, group)

    response = render(
        request,
        'group_space/_chat_composer.html',
        {
            **_group_context(user, group),
            'share_menu': _share_menu_for(user),
            'composer_form': form,
        },
        status=422,
    )
    response['HX-Retarget'] = '#chat-composer'
    response['HX-Reswap'] = 'outerHTML'
    return response


@login_required
@require_POST
def share_create(request):
    user = request.user
    if user.role != User.Role.STUDENT:
        raise Http404

    group = resolve_group(get_accessible_groups(user), request.POST.get('group_pk', ''))
    if not group:
        raise Http404

    kind = request.POST.get('kind', '')
    obj_id = request.POST.get('obj_id', '')
    if not obj_id.isdigit():
        raise Http404

    obj = snapshots.get_shareable_object(user, kind, int(obj_id))
    if obj is None:
        raise Http404

    group_space = get_group_space_for_group(group)
    snapshot_kind, snapshot_html, snapshot_meta = snapshots.build_snapshot_for_object(user, obj)

    post = Post(
        group_space=group_space,
        author=user,
        snapshot_kind=snapshot_kind,
        snapshot_html=snapshot_html,
        snapshot_meta=snapshot_meta,
    )
    post.full_clean()
    post.save()
    after_post_saved(post)
    return _bubble_response(request, post, group)


@login_required
def post_create(request):
    group = resolve_group(get_accessible_groups(request.user), request.GET.get('group', ''))
    if group:
        return _feed_redirect(group)
    return redirect('group_space:feed')


@login_required
def share_start(request):
    group = resolve_group(get_accessible_groups(request.user), request.GET.get('group', ''))
    if group:
        return _feed_redirect(group)
    return redirect('group_space:feed')


@login_required
def post_edit(request, pk):
    user = request.user
    post = get_post_or_404(user, pk)
    if not can_edit_post(user, post):
        raise Http404
    group = post.group

    if request.method == 'POST':
        form = PostForm(
            request.POST,
            request.FILES,
            instance=post,
            can_pin=can_pin_post(user, post),
        )
        if form.is_valid():
            post = form.save()
            after_post_saved(post)
            messages.success(request, 'Message updated.')
            return _feed_redirect(group)
    else:
        form = PostForm(instance=post, can_pin=can_pin_post(user, post))

    return render(request, 'group_space/post_form.html', {
        **_group_context(user, group),
        'form': form,
        'form_title': 'Edit message',
        'post': post,
    })


@login_required
def post_delete(request, pk):
    post = get_post_or_404(request.user, pk)
    if not can_delete_post(request.user, post):
        raise Http404
    group = post.group

    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Message removed.')
        return _feed_redirect(group)

    return render(request, 'group_space/post_confirm_delete.html', {
        'post': post,
        'group': group,
    })
