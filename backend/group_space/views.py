from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import User
from cohorts.models import Group

from .chat import ChatItem, build_chat_timeline
from .forms import ChatComposerForm, GoogleDocCreateForm, PostForm
from .models import Post, ProjectSpace
from .permissions import (
    can_delete_post,
    can_edit_post,
    can_pin_post,
    can_post_in_space,
    get_post_or_404,
)
from .constants import SHARE_KIND_PANEL
from google_storage.integration import should_upload_file_to_drive
from google_storage.orchestrator import (
    create_google_doc_for_post,
    prepare_drive_upload,
    retry_failed_drive_upload,
)
from google_storage.permissions import can_retry_drive_upload, delete_drive_file_for_post
from google_storage.rate_limit import DriveUploadRateLimitError
from google_storage.integration import composer_upload_context

from . import snapshots
from .notifications import notify_group_chat_post
from .services import after_post_saved, get_group_space_for_group, get_space_for_ref
from .space import SpaceRef, get_accessible_spaces, resolve_space_from_request


def _filtered_share_kind_panel():
    from config.module_access import is_module_enabled
    from config.modules import SNAPSHOT_KIND_TO_SLUG

    return tuple(
        (kind, label)
        for kind, label in SHARE_KIND_PANEL
        if is_module_enabled(SNAPSHOT_KIND_TO_SLUG.get(kind, ''))
    )


def _share_menu_for(user):
    if user.role != User.Role.STUDENT:
        return None
    return snapshots.build_share_menu(user)


def _group_for_ref(space_ref: SpaceRef | None):
    if space_ref is None or space_ref.kind != 'cohort_group':
        return None
    return Group.objects.filter(pk=space_ref.pk).select_related('cohort').first()


def _space_context(user, space_ref: SpaceRef | None, *, extra=None):
    group = _group_for_ref(space_ref)
    allow_file_upload = bool(space_ref and space_ref.kind == 'cohort_group' and not space_ref.is_archived)
    can_post = bool(space_ref) and can_post_in_space(user, space_ref)
    ctx = {
        'space_ref': space_ref,
        'available_spaces': get_accessible_spaces(user),
        'selected_space_kind': space_ref.kind if space_ref else '',
        'selected_space_pk': str(space_ref.pk) if space_ref else '',
        'can_post': can_post,
        'allow_file_upload': allow_file_upload,
        'resources_scope_label': space_ref.resources_scope_label if space_ref else 'group Resources list',
        'group': group,
        'available_groups': [g for g in ([group] if group else [])],
        'selected_group_pk': str(group.pk) if group else '',
        'share_kind_panel': _filtered_share_kind_panel(),
    }
    if extra:
        ctx.update(extra)
    return ctx


def _resolve_request_space(user, request, *, post_data=False, strict=False):
    source = request.POST if post_data else request.GET
    space_ref = resolve_space_from_request(user, source, strict=strict)
    return space_ref, get_space_for_ref(space_ref) if space_ref else None


def _feed_redirect(space_ref: SpaceRef):
    return redirect(f"{space_ref.feed_url()}#chat-bottom")


def _post_matches_space(post, space_ref: SpaceRef) -> bool:
    if space_ref.kind == 'cohort_group':
        return post.group_space_id is not None and post.group_space.group_id == space_ref.pk
    return post.project_space_id is not None and post.project_space_id == space_ref.pk


def _bubble_response(request, post, space_ref: SpaceRef):
    if not _post_matches_space(post, space_ref):
        raise Http404
    item = ChatItem(kind='post', created_at=post.created_at, post=post)
    response = render(request, 'group_space/_chat_bubble.html', {
        'item': item,
        'user': request.user,
        'space_ref': space_ref,
        'group': _group_for_ref(space_ref),
    })
    response['HX-Trigger'] = 'chatScrollBottom, closeSharePanel'
    return response


@login_required
def feed(request):
    user = request.user
    space_ref, space = _resolve_request_space(user, request)
    pinned_posts = []
    chat_items = []
    share_menu = _share_menu_for(user)
    project_space = None
    group_space = None
    if space_ref and space:
        if space_ref.kind == 'cohort_group':
            group_space = space
        else:
            project_space = space
        pinned_posts, chat_items = build_chat_timeline(space)

    return render(request, 'group_space/feed.html', {
        **_space_context(user, space_ref),
        'group_space': group_space,
        'project_space': project_space,
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
    space_ref, space = _resolve_request_space(user, request, post_data=True, strict=True)
    if not space_ref or space is None:
        raise Http404
    if not can_post_in_space(user, space_ref):
        raise Http404

    form = ChatComposerForm(request.POST, request.FILES, user=user)
    if form.is_valid():
        uploaded = form.cleaned_data.get('file')
        if uploaded and space_ref.kind == 'project':
            form.add_error('file', 'File attachments in project spaces are not supported yet.')
            return _composer_error_response(request, user, space_ref, composer_form=form)

        post = form.save(commit=False)
        post.author = user
        if space_ref.kind == 'cohort_group':
            post.group_space = space
            post.project_space = None
        else:
            post.project_space = space
            post.group_space = None
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
                return _composer_error_response(request, user, space_ref, composer_form=form)
        after_post_saved(post)
        if post.group_space_id:
            notify_group_chat_post(post)
        return _bubble_response(request, post, space_ref)

    return _composer_error_response(request, user, space_ref, composer_form=form)


def _composer_error_response(
    request,
    user,
    space_ref,
    *,
    composer_form=None,
    gdoc_form=None,
    initial_gdoc=False,
):
    response = render(
        request,
        'group_space/_chat_composer.html',
        {
            **_space_context(user, space_ref),
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
    space_ref, space = _resolve_request_space(user, request, post_data=True, strict=True)
    if not space_ref or space is None or space_ref.kind != 'cohort_group':
        raise Http404
    if not can_post_in_space(user, space_ref):
        raise Http404

    form = GoogleDocCreateForm(request.POST, user=user)
    if form.is_valid():
        post = Post(
            group_space=space,
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
            return _composer_error_response(request, user, space_ref, gdoc_form=form, initial_gdoc=True)
        except Exception as exc:
            post.delete()
            form.add_error(None, str(exc))
            return _composer_error_response(request, user, space_ref, gdoc_form=form, initial_gdoc=True)
        after_post_saved(post)
        notify_group_chat_post(post)
        return _bubble_response(request, post, space_ref)

    return _composer_error_response(request, user, space_ref, gdoc_form=form, initial_gdoc=True)


@login_required
@require_POST
def share_create(request):
    user = request.user
    if user.role != User.Role.STUDENT:
        raise Http404

    space_ref, space = _resolve_request_space(user, request, post_data=True, strict=True)
    if not space_ref or space is None or not can_post_in_space(user, space_ref):
        raise Http404

    kind = request.POST.get('kind', '')
    obj_id = request.POST.get('obj_id', '')
    if not obj_id.isdigit():
        raise Http404

    from config.module_access import is_module_enabled
    from config.modules import SNAPSHOT_KIND_TO_SLUG

    module_slug = SNAPSHOT_KIND_TO_SLUG.get(kind)
    if not module_slug or not is_module_enabled(module_slug):
        raise Http404

    obj = snapshots.get_shareable_object(user, kind, int(obj_id))
    if obj is None:
        raise Http404

    snapshot_kind, snapshot_html, snapshot_meta = snapshots.build_snapshot_for_object(user, obj)
    post = Post(
        author=user,
        snapshot_kind=snapshot_kind,
        snapshot_html=snapshot_html,
        snapshot_meta=snapshot_meta,
    )
    if space_ref.kind == 'cohort_group':
        post.group_space = space
    else:
        post.project_space = space
    post.full_clean()
    post.save()
    after_post_saved(post)
    if post.group_space_id:
        notify_group_chat_post(post)
    return _bubble_response(request, post, space_ref)


@login_required
@require_POST
def post_upload_retry(request, pk):
    user = request.user
    post = get_post_or_404(user, pk)
    space_ref = post.space_ref
    if not can_retry_drive_upload(user, post):
        raise Http404
    if not retry_failed_drive_upload(post):
        messages.error(request, 'Could not retry upload — staged file is no longer available.')
        return _bubble_response(request, post, space_ref)
    post.refresh_from_db()
    return _bubble_response(request, post, space_ref)


@login_required
def post_upload_poll(request, pk):
    user = request.user
    post = get_post_or_404(user, pk)
    space_ref = post.space_ref
    if post.drive_upload_status != Post.DriveUploadStatus.PENDING:
        return _bubble_response(request, post, space_ref)
    item = ChatItem(kind='post', created_at=post.created_at, post=post)
    return render(request, 'group_space/_chat_bubble.html', {
        'item': item,
        'user': user,
        'space_ref': space_ref,
        'group': _group_for_ref(space_ref),
    })


@login_required
def post_create(request):
    space_ref, _space = _resolve_request_space(request.user, request)
    if space_ref:
        return _feed_redirect(space_ref)
    return redirect('group_space:feed')


@login_required
def share_start(request):
    space_ref, _space = _resolve_request_space(request.user, request)
    if space_ref:
        return _feed_redirect(space_ref)
    return redirect('group_space:feed')


@login_required
def post_edit(request, pk):
    user = request.user
    post = get_post_or_404(user, pk)
    if not can_edit_post(user, post):
        raise Http404
    space_ref = post.space_ref

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
            return _feed_redirect(space_ref)
    else:
        form = PostForm(instance=post, can_pin=can_pin_post(user, post))

    return render(request, 'group_space/post_form.html', {
        **_space_context(user, space_ref),
        'form': form,
        'form_title': 'Edit message',
        'post': post,
    })


@login_required
def post_delete(request, pk):
    post = get_post_or_404(request.user, pk)
    if not can_delete_post(request.user, post):
        raise Http404
    space_ref = post.space_ref

    if request.method == 'POST':
        if post.drive_file_id and can_delete_post(request.user, post):
            try:
                delete_drive_file_for_post(post)
            except Exception:
                messages.warning(request, 'Post removed; Drive file may still exist.')
        post.delete()
        messages.success(request, 'Message removed.')
        return _feed_redirect(space_ref)

    return render(request, 'group_space/post_confirm_delete.html', {
        'post': post,
        'space_ref': space_ref,
        'group': _group_for_ref(space_ref),
    })
