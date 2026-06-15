## Group feed {#list}

One chronological chat for your study group. Everyone in the group can read and post.

### Badges on posts

| Badge | Meaning |
|-------|---------|
| **Shared · Journal / Habit / Goal / Task** | An **achievement snapshot** — a frozen preview card from your learning apps (see below). **Not** saved to Resources. |
| **Resource** | A **file or link** that was saved to the group’s Resources list because you gave it a resource name. |

Plain text posts (no file, no link, no snapshot) have no badge.

## Sharing snapshots {#snapshots}

Snapshots let you celebrate or discuss progress without copying private text by hand.

### How it works (students)

1. On the feed, open **Share** (panel order: Goal → Task → Journal → Habit).
2. Pick an item you already marked **shared with teachers** in that app (private items do not appear).
3. The app builds a **read-only card** in the chat: title, status, milestones/subtasks, journal date, habit week grid, etc.
4. The post is stored as HTML in chat only — classmates see the card in the thread.

### What a snapshot is **not**

- It is **not** a full copy of your private journal or a private task title.
- It does **not** create a link in **Resources**.
- Editing the original Goal/Task/Journal/Habit later does **not** update old snapshot posts — the card is a moment-in-time picture.

### What others see

- **Tasks / goals** — only items you set to **shared** visibility appear in the Share list.
- **Private tasks** stay out of Share; the snapshot uses what the template is designed to show (e.g. status, milestones), not hidden titles.

Teachers and admins do not use the Share panel the same way; they mainly post messages, files, and links.

## Files, links, and auto-save to Resources {#resources-sync}

When a post should become a **bookmark in Resources**, you must give it a **resource name** (label). That name becomes the link title on the group Resources tile.

### Qualifying posts (auto-sync)

After you **save** a new or edited post, the app may add or update one link in your group’s **system Resources container** (same name as the group) when **all** of this is true:

1. The post is **not** a snapshot-only share.
2. The post has a **file attachment** and/or a **http(s) link** in the message body.
3. You filled in **resource name** (required in the form when a file or link is present).

If you remove the file, link, or name on edit, the linked Resources entry is **removed**. Deleting the post deletes the linked entry too.

### File upload

- Attach a file in the composer (or edit form).
- Enter **resource name** — e.g. “Week 3 slides”.
- Allowed types include PDF, Word, text, common images (see form hint for full list); max size **10 MB**.
- When Google Drive is enabled, files upload to Drive (students: **My Drive** after connecting Google on Profile; staff: org **Shared drive**). The chat shows **Uploading…** then **Open in Google Drive**. Failed uploads can be **retried** from the message.
- **New Google file** (Doc, Sheet, Slides, Form) creates an empty file in the same Drive folder and adds it to Resources when you provide a name.
- The saved link in Resources points to the Drive (or legacy) file so the group can open it again later.

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

Open **Resources → Group tab** → open the tile named after your group → links with a **Group chat** badge came from chat. You may delete them manually; they will not reappear unless someone posts a **new** qualifying message.

## Create post {#form-create}

### Message

Optional if you attach a file, paste a link (with name), or publish a snapshot.

### Attach file

Upload + **resource name** → chat post with **Resource** badge + auto-sync to group Resources (see above).

### Paste a URL

Detected links trigger the resource name field; same sync behaviour.

### Share

Opens the snapshot picker (students, shared items only) — chat card only, no Resources sync.

## Edit post {#form-edit}

Change message, file, or resource name. Sync runs again: updates the Resources link, or removes it if the post no longer qualifies.

## Delete post {#form-delete}

Removes the post and any Resources item tied to it (`source_post`).

## For students {#for-students}

Use **Share** for progress cards, **file/link + name** for things the whole group should bookmark in Resources.

## Admin notes {#admin-only}

<!-- role: admin -->

Pinned posts and moderation use the same rules; sync is per group system container.
