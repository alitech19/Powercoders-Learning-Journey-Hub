# Group Space — Project Spaces (Custom Collaboration)

## Goal

Extend the existing **`group_space`** app so staff can create **project spaces**: temporary collaboration rooms with a custom member list (students from any cohort groups + staff), a dedicated chat, and a dedicated system Resources container.

**Not in scope:** multi-group academic membership (`User.group` stays 1:1). Project spaces do **not** grant access to another group’s tasks, goals, or workflows.

---

## Product decisions (agreed)

| Rule | Detail |
|------|--------|
| Academic group | Unchanged — one `cohorts.Group` per student; all assignment scoping unchanged |
| Project space | Collaboration only — chat + shared resource links |
| Membership | Staff creates space and adds/removes members; students cannot invite |
| **Who can join a project** | Students from **any cohort**; **any teacher** may be added; not limited to a teacher’s assigned cohort groups |
| **Admin** | Sees **all** project spaces and can **manage** them (create, edit title, members, archive) without being listed as a member |
| Student UX | Same pattern as teachers switching cohort groups: **list of accessible spaces → picker → one active feed** |
| **Picker order** | By creation: **academic group chat first** (auto-created with cohort group), then project spaces in **`ProjectSpace.created_at`** order as they are added |
| **Nav / page label** | UI tab name: **Чат** (replaces current “Group” nav label) |
| **Picker / header labels** | Academic entry = **cohort group name** (`Group.name`); custom entry = **`ProjectSpace.title`** set on create or edit |
| Achievement shares | Allowed in project chat for students (same snapshot types as group chat) |
| Archive | Staff can archive; archived = read-only chat, no new posts |
| Internal model name | `ProjectSpace` (product copy may say “project” in help text; picker shows `title`) |

---

## Why extend `group_space` (not a new app)

- Chat, forms, timeline, HTMX, and snapshots already live here.
- Teacher multi-group selector is already implemented (`get_accessible_groups` + `resolve_group`).
- One place to evolve shared chat behavior (composer, pins, file rules, future Drive/Slack hooks).

Trade-off: app name `group_space` becomes slightly broader (“spaces for groups and projects”). Nav and page title use **Чат**; pills distinguish academic (group name) vs custom (`title`).

---

## Current state (as-is)

| Piece | Location |
|-------|----------|
| `GroupSpace` 1:1 `cohorts.Group` | `group_space/models.py` |
| `Post` → `group_space` FK | `group_space/models.py` |
| Feed + HTMX | `group_space/views.py`, `templates/group_space/` |
| Accessible groups | `group_space/permissions.py` → `get_accessible_groups` |
| Resources sync | `group_space/services.py` → `resources.services.sync_from_group_post` |
| System group container | `resources` signal on `Group` create |

---

## Target architecture

### Space types in one app

```text
group_space/
  models.py          GroupSpace (unchanged role)
                     ProjectSpace + ProjectSpaceMembership (new)
                     Post (FK: exactly one parent space)
  space.py           SpaceContext dataclass + resolvers (new)
  permissions.py     group + project access helpers
  views.py           feed + CRUD; project admin views (staff)
  services.py        post/resources hooks parameterized by space kind
  chat.py            timeline keyed by space id + kind
  templates/         shared partials + thin wrappers per kind
```

### Unified “accessible spaces” for the feed

Introduce a small value object (no DB table):

```python
@dataclass(frozen=True)
class SpaceRef:
    kind: Literal['cohort_group', 'project']
    pk: int
    label: str          # Group.name or ProjectSpace.title
    subtitle: str       # e.g. cohort name for academic; optional member count for project
    sort_key: tuple     # stable ordering — see below
```

- `get_accessible_spaces(user) -> list[SpaceRef]` — **sorted before return**:
  1. **Academic** (`cohort_group`): for students, their single group if assigned; for teachers, all `get_teacher_group_ids`; for admins, all cohort groups (same as today’s group list). Each uses `label=group.name`, `subtitle=cohort.name`. `sort_key` uses group creation / cohort order (existing group ordering).
  2. **Project** (`project`): spaces the user is a member of, **or all spaces if admin**. `label=project.title`. Order by `ProjectSpace.created_at` ascending.
  - Cross-cohort membership is allowed; no `cohort_id` validation on add.

- `resolve_space(spaces, *, kind: str, pk: str) -> SpaceRef | None`  
  - Match query params; if missing, default to **`spaces[0]`** (always academic first when user has a group).

Query string (recommended):

```text
/group-space/?kind=cohort_group&space=12
/group-space/?kind=project&space=3
```

Backward compatibility for bookmarks:

- `?group=12` without `kind` → treated as `kind=cohort_group&space=12` (deprecated but supported one release).

---

## Data model changes

### 1) `ProjectSpace`

| Field | Type | Notes |
|-------|------|-------|
| `title` | CharField | Required, max title length from `config.input_limits` |
| `description` | TextField | Optional |
| `created_by` | FK `User` | Staff who created |
| `is_archived` | BooleanField | Default false |
| `created_at` / `updated_at` | DateTime | |

Indexes: `(is_archived, title)`, `(created_by,)`.

### 2) `ProjectSpaceMembership`

| Field | Type | Notes |
|-------|------|-------|
| `project_space` | FK `ProjectSpace` | CASCADE |
| `user` | FK `User` | CASCADE |
| `role` | CharField choices | `member` (students), `moderator` (teachers on the space) |
| `added_by` | FK `User` | Nullable for backfill |
| `created_at` | DateTime | Used for membership audit only; **space** ordering uses `ProjectSpace.created_at` |

Constraints:

- `UniqueConstraint(project_space, user)`
- **Students** → role `member` (any cohort).
- **Teachers** → role `moderator` when explicitly added to the space (any teacher in the org may be added).
- **Admin** does not need a membership row for access — global manage via `user.role == ADMIN` (may still post in chat when viewing any space).

**No cohort constraint** on membership.

### `ProjectSpace` edit

- Staff (and admin) can **edit `title`** (and description) after create; title is what appears in the **Чат** picker and page subtitle.

### 3) `Post` — dual parent (migration)

Add nullable FK:

```python
project_space = models.ForeignKey(
    'group_space.ProjectSpace',
    null=True,
    blank=True,
    on_delete=models.CASCADE,
    related_name='posts',
)
```

Make `group_space` **nullable** (existing rows keep `group_space_id` set).

**Constraint:** exactly one of `group_space_id`, `project_space_id` is non-null.

Update indexes: `(project_space, created_at)`, `(project_space, pinned)`.

Properties:

- `post.space_ref` → `SpaceRef`
- `post.group` — keep for cohort posts only (`group_space.group`); templates use `space_ref` where possible.

### 4) `resources.ResourceContainer`

Add:

| Change | Detail |
|--------|--------|
| `ContainerType.PROJECT` | New choice `'project', 'Project'` |
| `project_space` | FK `group_space.ProjectSpace`, null=True |
| Constraint | One system container per project: `UniqueConstraint(project_space, condition=is_system=True, container_type=PROJECT)` |

`group` FK remains for cohort containers only.

### 5) `resources.ResourceItem`

Keep `source_post` → `group_space.Post` (works for both parents).

Add property `from_project_chat` or generalize badge to **Space chat** with sub-label.

---

## Permissions

Central module shape (extend `group_space/permissions.py`):

| Function | Cohort group | Project space |
|----------|--------------|---------------|
| `can_access_space(user, space_ref)` | `can_access_group` | membership exists + not archived (read); archived = read-only |
| `can_post_in_space` | existing | member + not archived |
| `can_edit_post` | author + access | same |
| `can_delete_post` | author or teacher/admin | author or **moderator** on project |
| `can_pin_post` | author or teacher/admin | author or moderator |
| `can_manage_project_space` | — | **admin always**; else teacher who is moderator on that space or `created_by` |
| `can_list_all_project_spaces` | — | teacher: spaces they moderate or created; **admin: all** |
| `get_post_or_404` | select_related both parents | |

**Do not** reuse `cohorts.permissions.can_access_group` for project membership.

---

## Services & resources sync

Refactor `group_space/services.py`:

| Function | Change |
|----------|--------|
| `post_qualifies_for_resources` | unchanged logic |
| `after_post_saved` | dispatch by parent kind |
| `sync_resource_from_post(post)` | new name; calls `resources.services.sync_from_space_post(post)` |
| `get_space_for_ref(space_ref)` | returns `GroupSpace` or `ProjectSpace` instance |

`resources/services.py`:

| Function | Change |
|----------|--------|
| `ensure_system_group_container(group)` | unchanged |
| `ensure_system_project_container(project_space)` | new, mirror group helper |
| `sync_from_space_post(post)` | replaces direct `sync_from_group_post` usage; picks container by post parent |

Signal on `ProjectSpace` post_save: create system project container (mirror `resources/signals.py` for `Group`).

---

## Views & URLs

### Chat (existing routes, generalized)

| Route | Notes |
|-------|-------|
| `GET /group-space/` | `feed` — uses `SpaceRef`, unified template |
| `POST .../send/` | `space_kind` + `space_pk` hidden fields (keep `group_pk` alias one release) |
| `POST .../share/` | only if student + space allows snapshots (both kinds) |
| post edit/delete | unchanged URLs; permission uses post’s parent |

### Project administration (staff)

New routes under same app (`app_name = 'group_space'`):

| Route | View | Who |
|-------|------|-----|
| `GET /group-space/projects/` | list project spaces | teacher (own/member) / **admin (all)** |
| `GET/POST .../projects/new/` | create (+ set `title`) | teacher / admin |
| `GET/POST .../projects/<pk>/` | detail, edit title, member list | `can_manage_project_space` |
| `POST .../projects/<pk>/members/add/` | students (any cohort) + teachers | moderators + admin |
| `POST .../projects/<pk>/members/<user_pk>/remove/` | | moderators + admin |
| `POST .../projects/<pk>/archive/` | | moderators + admin |

Students: no admin UI; they only see spaces they belong to in the **Чат** picker.

Member picker (staff UI): students filtered by cohort/group for usability, but **cross-cohort add is allowed** (search by name / email if needed in Phase 1+).

---

## Templates & frontend

### Parameterize shared partials

Rename or alias includes to accept context:

| Partial | Parameters |
|---------|------------|
| `_chat_feed_shell.html` | `space_ref`, `available_spaces`, `chat_items`, `pinned_posts` |
| `_chat_composer.html` | `space_kind`, `space_pk`, `composer_form`, `share_menu` |
| `_chat_bubble.html` | `item`, `user`, `space_ref` |
| `_space_picker.html` | pills linking `?kind=&space=` |

Keep `feed.html` as wrapper:

- Page `<title>` / H1: **Чат**
- Subtitle under H1: academic → `{group.name} · {cohort.name}`; project → `{project.title}` (optional description line)
- Picker pills: academic shows **group name**; project shows **`title`**; order per `get_accessible_spaces` (academic first, then projects by creation)
- Show picker when `len(available_spaces) > 1`

### Copy tweaks

- Composer hidden field: `space_kind` + `space_pk`
- Resource validation messages: “group Resources list” → “project Resources list” when `kind=project` (template `if` or pass `resources_scope_label`).

### Dashboard

`dashboard/views.py` + template:

- Quick link **Project spaces** (staff → list; student → feed with first project if any)
- Optional tile: count of active project memberships

### Nav

`config/nav.py`: rename nav item label from `Group` to **`Чат`** (URL stays `group_space:feed`).  
`info/registry.py`: update help label for `group_space:feed` to **Чат**.

---

## Chat timeline (`chat.py`)

`build_chat_timeline(space)`:

- Accept `GroupSpace` or `ProjectSpace` (or `SpaceRef` + loader).
- Query `Post.objects.filter(Q(group_space=...) | Q(project_space=...))`.
- `ChatItem` unchanged.

---

## Admin

`group_space/admin.py`:

- `ProjectSpace` inline memberships
- Read-only post list per project
- Actions: archive / unarchive

---

## Migrations & rollout

### Migration order

1. Create `ProjectSpace`, `ProjectSpaceMembership`
2. Alter `Post`: nullable `group_space`, add `project_space`, check constraint
3. Alter `ResourceContainer`: type + `project_space` FK + constraint
4. Data migration: none required for existing posts

### Phased delivery

#### Phase 0 — Foundation (backend only)

- Models + migrations
- Permissions + `SpaceRef` helpers
- `ensure_system_project_container` + `sync_from_space_post`
- Unit tests: membership, access, sync qualifies

#### Phase 1 — Staff project CRUD

- List/create/edit members/archive views
- No student-facing picker yet (staff can smoke-test via direct URL)

#### Phase 2 — Unified chat feed

- Refactor `feed`, `message_create`, `share_create`, partials
- `?kind=&space=` + backward compatible `?group=`
- Student multi-space picker

#### Phase 3 — Resources UI

- Resources index: **Project** tab (or subsection under Group tab — prefer **separate tab** to avoid mixing cohort group tiles with ad-hoc projects)
- Container detail badge: **Project chat**
- Link from project space header → Resources container

#### Phase 4 — Docs & polish

- `info/topics/group_space.md` — project section
- Help registry entries
- Dashboard copy

### Out of scope for v1

- Slack sync per project channel
- Google Drive folder `PowerHUB/Projects/{space}/` (follow-up after [GOOGLE_DRIVE_INTEGRATION_PLAN.md](GOOGLE_DRIVE_INTEGRATION_PLAN.md); extend folder resolver by `space.kind`)
- Comments on posts (if not exposed in UI today, keep deferred)
- Student-created spaces

---

## Testing plan

| Area | Tests |
|------|-------|
| `group_space/tests/test_permissions.py` | project access, archive read-only, moderator delete |
| `group_space/tests/test_services.py` | `sync_from_space_post` for project posts |
| `group_space/tests/test_chat.py` | timeline for project space |
| New `test_project_spaces.py` | CRUD, membership add/remove, archive |
| `resources/tests/test_services.py` | `ensure_system_project_container` |
| `tests/test_cross_app.py` | students from cohort A + cohort B in one project; no task leakage |
| `test_permissions.py` | admin manages project without membership row; teacher added from another cohort |

Factories: `test_utils/group_space.py` — `make_project_space`, `add_member`.

---

## Files to touch (checklist)

### `group_space`

- `models.py`, `migrations/`
- `space.py` (new)
- `permissions.py`, `services.py`, `chat.py`, `views.py`, `urls.py`, `forms.py`, `admin.py`, `signals.py` (project container on create)
- `templates/group_space/*`
- `tests/*`

### `resources`

- `models.py`, `migrations/`
- `services.py`, `permissions.py`, `views.py` (project tab)
- `templates/resources/index.html`, `container_detail.html`
- `tests/test_permissions.py`, `tests/test_services.py`

### Other

- `dashboard/views.py`, `templates/dashboard/dashboard.html`
- `config/nav.py` — label **Чат**
- `info/registry.py`, `info/topics/group_space.md`
- [TODO.md](TODO.md) — index

---

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| `Post` FK confusion | DB check constraint; factory helpers always set one parent |
| Template regression for teachers | Keep `?group=` shim; exhaustive HTMX tests |
| Permission leak to other group’s tasks | Never join project membership into tasks/goals querysets |
| Two chat UIs diverge again | Single partial set; code review rule: change chat in one partial only |
| Resources tab clutter | Separate **Project** tab, not mixed into cohort group system tiles |

---

## UI copy (agreed)

| Place | Text |
|-------|------|
| Main nav | **Чат** |
| Page heading | **Чат** |
| Picker pill (academic) | `{Group.name}` |
| Picker pill (custom) | `{ProjectSpace.title}` |
| Staff project form | Title (required), description (optional); edit on space detail |

---


## Success criteria (MVP)

- [ ] Staff creates a project space and adds students from two different cohorts + a teacher not assigned to those groups
- [ ] Admin lists and edits any project space without membership
- [ ] Each student sees academic group (first pill, group name) then project spaces by creation date
- [ ] Nav shows **Чат**; custom space shows chosen title in picker and subtitle
- [ ] Teacher with multiple cohort groups still uses same feed UX (no regression)
- [ ] File/link + `resource_label` post syncs to project system container with correct badge
- [ ] Archived project: feed readable, composer hidden, sync disabled
- [ ] No change to task/goal/workflow visibility based on project membership

---

## Related docs

- [GOOGLE_DRIVE_INTEGRATION_PLAN.md](GOOGLE_DRIVE_INTEGRATION_PLAN.md) — Drive uploads (v1 local `media/group_files/` until then)
- [GOOGLE_DRIVE_INTEGRATION_PLAN.md](GOOGLE_DRIVE_INTEGRATION_PLAN.md) — future per-space Drive folders
- [SLACK_INTEGRATION_PLAN.md](SLACK_INTEGRATION_PLAN.md) — group channel sync; project channels later
