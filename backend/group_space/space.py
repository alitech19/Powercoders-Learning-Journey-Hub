"""Unified space references for academic groups and project spaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from django.urls import reverse

from cohorts.models import Group

from .models import GroupSpace, ProjectSpace


@dataclass(frozen=True)
class SpaceRef:
    kind: Literal['cohort_group', 'project']
    pk: int
    label: str
    subtitle: str
    sort_key: tuple
    is_archived: bool = False

    def feed_url(self) -> str:
        return f"{reverse('group_space:feed')}?kind={self.kind}&space={self.pk}"

    @property
    def resources_scope_label(self) -> str:
        if self.kind == 'project':
            return 'project Resources list'
        return 'group Resources list'

def _academic_space_refs(user) -> list[SpaceRef]:
    from .permissions import get_accessible_groups

    refs: list[SpaceRef] = []
    for group in get_accessible_groups(user):
        refs.append(
            SpaceRef(
                kind='cohort_group',
                pk=group.pk,
                label=group.name,
                subtitle=group.cohort.name,
                sort_key=(0, group.cohort.name, group.name, group.pk),
            ),
        )
    return refs


def _project_space_refs(user) -> list[SpaceRef]:
    from .permissions import get_accessible_project_spaces

    refs: list[SpaceRef] = []
    for project in get_accessible_project_spaces(user):
        member_count = project.memberships.count()
        refs.append(
            SpaceRef(
                kind='project',
                pk=project.pk,
                label=project.title,
                subtitle=f'{member_count} member{"s" if member_count != 1 else ""}',
                sort_key=(1, project.created_at, project.pk),
                is_archived=project.is_archived,
            ),
        )
    return refs


def get_accessible_spaces(user) -> list[SpaceRef]:
    if not user.is_authenticated:
        return []
    spaces = _academic_space_refs(user) + _project_space_refs(user)
    return sorted(spaces, key=lambda ref: ref.sort_key)


def resolve_space(spaces: list[SpaceRef], *, kind: str = '', pk: str = '', legacy_group_pk: str = '') -> SpaceRef | None:
    if not spaces:
        return None
    kind = (kind or '').strip()
    pk = (pk or '').strip()
    legacy_group_pk = (legacy_group_pk or '').strip()
    if kind and pk:
        return next(
            (space for space in spaces if space.kind == kind and str(space.pk) == str(pk)),
            None,
        )
    if not kind and legacy_group_pk:
        kind = 'cohort_group'
        pk = legacy_group_pk
        return next(
            (space for space in spaces if space.kind == kind and str(space.pk) == str(pk)),
            None,
        )
    return spaces[0]


def _space_params_from_source(source) -> tuple[str, str, str]:
    """Form POST uses space_kind/space_pk; feed URLs use kind/space; legacy uses group/group_pk."""
    kind = (source.get('space_kind') or source.get('kind') or '').strip()
    pk = (source.get('space_pk') or source.get('space') or '').strip()
    legacy = (source.get('group_pk') or source.get('group') or '').strip()
    return kind, pk, legacy


def resolve_space_from_request(user, source, *, strict: bool = False) -> SpaceRef | None:
    """Resolve the active chat space from GET/POST params.

    When strict=True (POST), kind+space_pk must match exactly — no fallback to the
    first cohort group (avoids posts leaking into the wrong chat).
    """
    spaces = get_accessible_spaces(user)
    kind, pk, legacy = _space_params_from_source(source)
    if strict:
        if kind and pk:
            return resolve_space(spaces, kind=kind, pk=pk)
        if legacy:
            return resolve_space(spaces, kind='', pk='', legacy_group_pk=legacy)
        return None
    return resolve_space(spaces, kind=kind, pk=pk, legacy_group_pk=legacy)


def get_group_space_for_ref(space_ref: SpaceRef) -> GroupSpace | None:
    if space_ref.kind != 'cohort_group':
        return None
    group = Group.objects.filter(pk=space_ref.pk).first()
    if group is None:
        return None
    from .services import get_group_space_for_group

    return get_group_space_for_group(group)


def get_project_space_for_ref(space_ref: SpaceRef) -> ProjectSpace | None:
    if space_ref.kind != 'project':
        return None
    return ProjectSpace.objects.filter(pk=space_ref.pk).first()


def post_space_ref(post) -> SpaceRef:
    if post.group_space_id:
        group = post.group_space.group
        return SpaceRef(
            kind='cohort_group',
            pk=group.pk,
            label=group.name,
            subtitle=group.cohort.name,
            sort_key=(0, group.cohort.name, group.name, group.pk),
        )
    project = post.project_space
    member_count = project.memberships.count()
    return SpaceRef(
        kind='project',
        pk=project.pk,
        label=project.title,
        subtitle=f'{member_count} member{"s" if member_count != 1 else ""}',
        sort_key=(1, project.created_at, project.pk),
        is_archived=project.is_archived,
    )
