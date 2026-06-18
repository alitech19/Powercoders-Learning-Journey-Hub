Group Space is the chat hub for your learning community. Each message belongs to **exactly one** space — cohort group or custom group space. Use the **pills** at the top of the feed to switch; the subtitle shows which space you are in.

## Two kinds of space {#space-types}

| Type | How it is created | Who is in it | Label on feed |
|------|-------------------|--------------|---------------|
| **Cohort group** | Automatically when a student is assigned to a group under **Cohorts & Groups** | Students in that academic group + assigned teachers + admins | `Cohort group · {name} · {cohort}` |
| **Custom group space** | Admin creates it under **Administration → Group spaces** | Anyone the admin adds (students/teachers from any cohort) | `Custom group space · {title}` |

Cohort groups follow academic placement (`User.group`). Custom spaces use a **separate membership list** — joining a project space does **not** move a student to another cohort group and does **not** change task or goal assignment.

## Switching between chats {#switching}

If you have access to more than one space, pills appear above the chat:

1. Click a pill — the page reloads with that space’s history and composer.
2. Check the subtitle under **Group Space** before you post.
3. Messages you send appear **only** in the active space (not in other groups or projects).

**Teachers** with several assigned groups see one pill per group and can write in each chat separately, the same way as before.

**Archived** custom group spaces are hidden from the picker and are read-only. Active cohort group chats are always listed.

## Group feed {#list}

One chronological thread per space. Everyone who can access that space can read and post (unless the custom space is archived).

### Badges on posts

| Badge | Meaning |
|-------|---------|
| **Shared · Journal / Habit / Goal / Task** | An **achievement snapshot** — a frozen preview card from your learning apps (see below). **Not** saved to Resources. |
| **Resource** | A **file or link** that was saved to the space’s Resources list because you gave it a resource name. |

Plain text posts (no file, no link, no snapshot) have no badge.

## Sharing snapshots {#snapshots}

Snapshots let you celebrate or discuss progress without copying private text by hand.

### How it works (students)

1. On the feed, open **Share** (panel order: Goal → Task → Journal → Habit).
2. Pick an item you already marked **shared with teachers** in that app (private items do not appear).
3. The app builds a **read-only card** in the chat: title, status, milestones/subtasks, journal date, habit week grid, etc.
4. The post is stored in chat only — classmates see the card in the thread.

### What a snapshot is **not**

- It is **not** a full copy of your private journal or a private task title.
- It does **not** create a link in **Resources**.
- Editing the original Goal/Task/Journal/Habit later does **not** update old snapshot posts — the card is a moment-in-time picture.

### What others see

- **Tasks / goals** — only items you set to **shared** visibility appear in the Share list.
- **Private tasks** stay out of Share; the snapshot uses what the template is designed to show (e.g. status, milestones), not hidden titles.

Teachers and admins do not use the Share panel the same way; they mainly post messages, files, and links.

## Files, links, and auto-save to Resources {#resources-sync}

When a post should become a **bookmark in Resources**, you must give it a **resource name** (label). That name becomes the link title on the Resources tile.

### Qualifying posts (auto-sync)

After you **save** a new or edited post, the app may add or update one link in the space’s **system Resources container** when **all** of this is true:

1. The post is **not** a snapshot-only share.
2. The post has a **file attachment** and/or a **http(s) link** in the message body.
3. You filled in **resource name** (required in the form when a file or link is present).

If you remove the file, link, or name on edit, the linked Resources entry is **removed**. Deleting the post deletes the linked entry too.

### Cohort group vs custom space

| Space type | Resources tab | Container name |
|------------|-----------------|----------------|
| Cohort group | **Group** | Same as the group name |
| Custom group space | **Group spaces** | Same as the space title |

### File upload

- **Cohort group chats** — attach a file in the composer (or edit form), with **resource name**. Allowed types include PDF, Word, text, common images; max size **10 MB**.
- **Custom group spaces** — text and links only for now (file attachments not supported yet).
- When Google Drive is enabled, cohort uploads go to Drive (students: **My Drive** after connecting Google on Profile; staff: org **Shared drive**). The chat shows **Uploading…** then **Open in Google Drive**. Failed uploads can be **retried** from the message.
- **New Google file** (Doc, Sheet, Slides, Form) is available in **cohort group** chats when Drive is configured.

### Link in message

- Paste a URL in the message (e.g. `https://…`).
- When the app detects a link, it asks for a **resource name**.
- Resources stores the **first** URL found in the message as the link target.

### What does **not** auto-sync

- Snapshot-only posts (Share).
- Text-only posts with no URL and no file.
- Posts with a file/link but **empty** resource name (validation should block save).
- **Old posts** from before auto-sync existed — only posts saved after this feature was enabled are synced (no automatic backfill).

### Where to find synced items

Open **Resources** → **Group** or **Group spaces** tab → open the tile named after your group or project → links with a **Group chat** badge came from chat. You may delete them manually; they will not reappear unless someone posts a **new** qualifying message.

## Create post {#form-create}

### Message

Optional if you attach a file, paste a link (with name), or publish a snapshot.

### Attach file

Cohort groups only: upload + **resource name** → chat post with **Resource** badge + auto-sync to group Resources (see above).

### Paste a URL

Detected links trigger the resource name field; same sync behaviour (cohort and custom spaces).

### Share

Opens the snapshot picker (students, shared items only) — chat card only, no Resources sync.

## Edit post {#form-edit}

Change message, file, or resource name. Sync runs again: updates the Resources link, or removes it if the post no longer qualifies.

## Delete post {#form-delete}

Removes the post and any Resources item tied to it (`source_post`).

## For students {#for-students}

Use **Share** for progress cards, **file/link + name** for things the whole group should bookmark in Resources. If you are in a custom group space, use links and text; file upload is for cohort group chats.

## For teachers {#for-teachers}

You see every cohort group you teach plus any custom group spaces you were added to. Switch pills before posting — each chat is independent. Moderators on a custom space can delete others’ messages; in cohort groups, teachers and admins can moderate.

## Admin notes {#admin-only}

<!-- role: admin -->

- Custom group spaces are managed under **Administration → Group spaces** (see that page’s **ⓘ** help).
- **Archive** ends active chat for a custom space; archived spaces disappear from the feed picker and admin list (restore via Django admin if needed).
- Pinned posts and moderation follow the same rules per space; Resources sync uses the matching system container.
