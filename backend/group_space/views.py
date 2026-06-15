from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import User

from .chat import ChatItem, build_chat_timeline
from .forms import ChatComposerForm, GoogleDocCreateForm, PostForm
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
from google_storage.integration import composer_upload_context
from google_storage.integration import should_upload_file_to_drive
from google_storage.orchestrator import (
    create_google_doc_for_post,
    prepare_drive_upload,
    retry_failed_drive_upload,
)
from google_storage.permissions import can_retry_drive_upload, delete_drive_file_for_post
from google_storage.rate_limit import DriveUploadRateLimitError

from .services import after_post_saved, get_group_space_for_group, load_post, resolve_group
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
        'composer_form': ChatComposerForm(user=user),
        'gdoc_form': GoogleDocCreateForm(user=user),
        **composer_upload_context(user),
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

    form = ChatComposerForm(request.POST, request.FILES, user=user)
    if form.is_valid():
        uploaded = form.cleaned_data.get('file')
        post = form.save(commit=False)
        post.author = user
        post.group_space = group_space
        use_drive = bool(uploaded) and should_upload_file_to_drive(user)
        if use_drive:
            post.file = None
        post.save()
        if use_drive:
            try:
                prepare_drive_upload(post, user, uploaded)
                post.refresh_from_db()
            except DriveUploadRateLimitError as exc:
                post.delete()
                form.add_error('file', str(exc))
                return _composer_error_response(
                    request, user, group, composer_form=form,
                )
        after_post_saved(post)
        return _bubble_response(request, post, group)

    return _composer_error_response(request, user, group, composer_form=form)


def _composer_error_response(
    request,
    user,
    group,
    *,
    composer_form=None,
    gdoc_form=None,
    initial_gdoc=False,
):
    response = render(
        request,
        'group_space/_chat_composer.html',
        {
            **_group_context(user, group),
            'share_menu': _share_menu_for(user),
            'composer_form': composer_form or ChatComposerForm(user=user),
            'gdoc_form': gdoc_form or GoogleDocCreateForm(user=user),
            **composer_upload_context(user),
        },
        status=422,
    )
    if initial_gdoc:
        response['HX-Trigger-After-Swap'] = 'openGdocMode'
    response['HX-Retarget'] = '#chat-composer'
    response['HX-Reswap'] = 'outerHTML'
    return response


@login_required
@require_POST
def google_doc_create(request):
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

    form = GoogleDocCreateForm(request.POST, user=user)
    if form.is_valid():
        post = Post(
            group_space=group_space,
            author=user,
            body=form.cleaned_data.get('body', ''),
            resource_label=form.cleaned_data['resource_label'],
        )
        post.save()
        try:
            create_google_doc_for_post(
                post,
                user,
                doc_kind=form.cleaned_data['doc_kind'],
                title=form.cleaned_data['resource_label'],
            )
        except DriveUploadRateLimitError as exc:
            post.delete()
            form.add_error(None, str(exc))
            return _composer_error_response(request, user, group, gdoc_form=form, initial_gdoc=True)
        except Exception as exc:
            post.delete()
            form.add_error(None, str(exc))
            return _composer_error_response(request, user, group, gdoc_form=form, initial_gdoc=True)
        after_post_saved(post)
        return _bubble_response(request, post, group)

    return _composer_error_response(request, user, group, gdoc_form=form, initial_gdoc=True)


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
@require_POST
def post_upload_retry(request, pk):
    """Re-enqueue a failed Drive upload (author only, staged file must exist)."""
    user = request.user
    post = get_post_or_404(user, pk)
    group = post.group
    if not can_retry_drive_upload(user, post):
        raise Http404
    if not retry_failed_drive_upload(post):
        messages.error(request, 'Could not retry upload — staged file is no longer available.')
        return _bubble_response(request, post, group)
    post.refresh_from_db()
    return _bubble_response(request, post, group)


@login_required
def post_upload_poll(request, pk):
    """HTMX poll while a Drive upload is pending."""
    user = request.user
    post = get_post_or_404(user, pk)
    group = post.group
    if post.drive_upload_status != Post.DriveUploadStatus.PENDING:
        return _bubble_response(request, post, group)
    item = ChatItem(kind='post', created_at=post.created_at, post=post)
    return render(request, 'group_space/_chat_bubble.html', {
        'item': item,
        'user': user,
        'group': group,
    })


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
        if post.drive_file_id and can_delete_post(request.user, post):
            try:
                delete_drive_file_for_post(post)
            except Exception:
                messages.warning(request, 'Post removed; Drive file may still exist.')
        post.delete()
        messages.success(request, 'Message removed.')
        return _feed_redirect(group)

    return render(request, 'group_space/post_confirm_delete.html', {
        'post': post,
        'group': group,
    })
