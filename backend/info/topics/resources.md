## Resources index {#list}

Three tabs organise **containers** (tiles). Open a tile to see an ordered list of links.

| Tab | What you see |
|-----|----------------|
| **My** | Personal link lists you created — only you manage them. |
| **Group** | One **system tile per study group** (named like the group) — holds links auto-saved from Group chat plus any staff setup. |
| **Themes** | Extra themed collections for a group (e.g. “Interview prep”, “React docs”) — created manually. |

If you belong to several groups, use the group chips on Group/Themes tabs to switch.

## Container types {#containers}

### Personal (`My` tab)

- **Who:** one student (you).
- **Purpose:** your own bookmarks — tutorials, tools, notes not tied to chat.
- **Create:** **+ New list** — you choose the tile name.
- **Links:** you add title + URL by hand on the detail page.
- **Not** filled automatically from Group chat.

### Group system container (`Group` tab)

- **Who:** one container per cohort **group**, created automatically (title = group name, e.g. “Bern”).
- **Purpose:** central list of **files and links** the team posted in Group chat with a resource name.
- **You cannot delete** the system tile itself; you can delete individual links inside it.
- **Not** used for achievement snapshots (those stay in chat only).

### Thematic (`Themes` tab)

- **Who:** tied to a group; created by students/teachers allowed to manage themes, or **linked from staff workflow / task / goal forms** (create or pick a theme).
- **Purpose:** curated topic boards (reading list, employer links, programme materials) — **manual** links on the theme detail page, or opened from **Open materials** on a linked entity.
- **Create:** **+ New theme** on Resources, or **Create new** in a workflow/task/goal form — you name the tile; add links on the detail page.
- **Separate** from chat auto-sync — chat does not push into theme tiles unless you copy links yourself.

### Entity-linked materials (workflows, tasks, goals)

Staff can attach an optional thematic container when creating or editing a **workflow**, **staff task**, or **staff goal**:

| Option | Result |
|--------|--------|
| **None** | No materials link on the entity detail page. |
| **Link existing theme** | Picker lists thematic boards (not system group tiles). |
| **Create new** | New theme; default title `Materials: {entity title}` (editable). |

Anyone who can view the entity sees **Open materials** on its detail page (assignees do not need to belong to a specific group tile).

## Auto-sync from Group chat {#group-chat-sync}

### When a link appears automatically

When someone in your group saves a chat post that has:

- a **file** and/or a **detected URL**, and  
- a filled **resource name**, and  
- **no** snapshot-only share,

the app creates or updates one **Resource item** inside that group’s **system container**.

| Detail | Behaviour |
|--------|-----------|
| **Link title** | The resource name from the chat form. |
| **URL** | First `http(s)` link in the message, or the uploaded file’s download URL. |
| **Badge** | **Group chat** on the item — means it came from a post (`source_post`). |
| **Edit post** | Changing file, link, or name updates or removes the Resources item. |
| **Delete post** | Removes the linked item (database cascade). |

### When auto-sync does **not** run

- **Share / snapshot** posts (Goal, Task, Journal, Habit cards).
- Text-only messages.
- File or link **without** resource name (should not save).
- **Historical posts** before auto-sync was enabled — only **new saves** after that (no backfill of old chat).

### Manual cleanup

You may **delete** an auto-synced link from the container detail page. It will **not** come back unless someone posts a **new** qualifying message (or edits an old post to qualify again).

Deleting a link does **not** delete the chat post.

### Multiple groups

If you are in more than one group, each group has its **own** system container on the **Group** tab — chat posts only sync into **their** group’s tile.

## Container detail {#detail}

Ordered links. Reorder when you have edit permission. Items from chat show **Group chat**.

## Create container {#form-create}

### Name (required)

Tile title on the index.

- **My** — personal list.
- **Themes** — thematic board for the selected group (not the system group tile).

You do not create the system group container manually.

## Create link item {#form-create}

### Title

Label in the list.

### URL

Full `https://…` address.

Manual items have no **Group chat** badge. Prefer fixing chat posts for synced items so post and link stay aligned.

## Edit container / item {#form-edit}

Rename tiles (except system group tile name follows group name). Edit link title or URL. System container title updates if the group is renamed.

## Delete {#form-delete}

Deleting a container removes **all** links inside. Deleting one item removes only that bookmark.

## For students {#for-students}

Use **Group** tab for “what we dropped in chat”. Use **My** for private study links. Use **Themes** when the cohort agrees on a shared reading board.

## Admin notes {#admin-only}

<!-- role: admin -->

Django admin can inspect containers and `source_post` links. One system container per group is enforced in the database.
