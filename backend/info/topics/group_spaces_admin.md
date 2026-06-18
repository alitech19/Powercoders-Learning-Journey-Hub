Custom **group spaces** let you run short-term or cross-cohort collaboration outside the academic group structure. Configure them on **Administration → Group spaces**. Use the **ⓘ** button on that page for this guide.

## Overview {#overview}

<!-- role: admin -->

| | Cohort group chat | Custom group space |
|---|-------------------|-------------------|
| **Created** | Automatically with **Cohorts & Groups** | **Administration → Group spaces → New** |
| **Membership** | Student’s assigned group + group teachers | Explicit list you manage |
| **Affects tasks/goals** | Yes (group-scoped work) | No |
| **Chat entry** | **Group Space** nav → pill with group name | Same nav → pill with space title |
| **Resources** | **Resources → Group** tab | **Resources → Group spaces** tab |

Students and teachers never create custom spaces themselves — only admins.

## Create a space {#create}

<!-- role: admin -->

1. Open **Administration → Group spaces**.
2. Click **New group space**.
3. Set **title** (shown in the chat picker) and optional **description**.
4. Save — you land on the member management page.

Titles should be distinct; they appear as pills alongside cohort group names on **Group Space**.

## Members {#members}

<!-- role: admin -->

On the space detail page:

| Action | Notes |
|--------|--------|
| **Add member** | Pick any user (student or teacher). Students can be from different cohorts. |
| **Moderator** | Teachers (or staff) can be moderators — they can delete others’ posts in that space. |
| **Remove** | Revokes chat and Resources access for that space only. |

Adding someone does **not** change their academic `User.group` or cohort enrollment.

## Open chat {#chat}

<!-- role: admin -->

From the space detail page, use **Open chat** (or **Group Space** → select the space pill).

- Admins can read and post in any custom space without being on the member list.
- Messages belong only to this space — they do not appear in cohort group chats.
- **Text and links** work; **file attachments and New Google file** are cohort-group features only for now.

Tell members to confirm the subtitle says **Custom group space · {title}** before posting.

## Archive {#archive}

<!-- role: admin -->

When collaboration ends:

1. On the space detail page, click **Archive**.
2. The space becomes **read-only** (no new posts).
3. It is **removed** from the **Group Space** picker, **Group spaces** admin list, and **Resources → Group spaces** tab so lists stay short.

To restore an archived space, use **Django admin** → **Project spaces** → select the row → action **Mark unarchived** (or edit `is_archived`). Then it reappears in admin and chat.

Archiving does **not** delete chat history or Resources items in the database.

## Tips {#tips}

<!-- role: admin -->

- Use custom spaces for hackathons, mentor circles, or staff-only projects — not as a replacement for cohort groups.
- Keep cohort placement in **Cohorts & Groups**; use this tool only for the extra room.
- Archive finished spaces instead of leaving them in the picker.
