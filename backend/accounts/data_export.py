"""Build a GDPR-style Markdown export of all data linked to a user."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

User = get_user_model()


def _iso(val):
    if val is None:
        return '—'
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return str(val)


def _md_escape_block(text: str) -> str:
    if not text:
        return '_empty_'
    return text.replace('\r\n', '\n')


def _section(title: str, lines: list[str]) -> list[str]:
    out = [f'## {title}', '']
    out.extend(lines)
    out.extend(['', '---', ''])
    return out


def build_user_data_markdown(user) -> str:
    from cohorts.models import GroupTeacher
    from feedback.models import FeedbackEntry
    from goals.models import Goal, GoalEnrollment
    from group_space.models import Comment, Post
    from habits.models import Habit, HabitLog
    from journal.models import JournalEntry
    from reflections.models import Reflection
    from resources.models import ResourceContainer, ResourceItem
    from tasks.models import Subtask, Task, TaskComment, TaskEnrollment, TaskUpdate
    from workflows.models import StepCompletion, Workflow, WorkflowEnrollment

    lines = [
        f'# Powercoders Data Export — {user.display_name}',
        '',
        f'Exported at: {_iso(timezone.now())}',
        '',
        '---',
        '',
    ]

    # Profile
    profile_lines = [
        f'- **Email:** {user.email}',
        f'- **Display name:** {user.display_name}',
        f'- **Role:** {user.get_role_display()}',
        f'- **Cohort:** {user.cohort or "—"}',
        f'- **Group:** {user.group or "—"}',
        f'- **Joined:** {_iso(user.date_joined)}',
        f'- **Last login:** {_iso(user.last_login)}',
        f'- **Email notifications:** {"on" if user.email_notifications_enabled else "off"}',
        f'- **Privacy policy accepted:** {_iso(user.privacy_policy_accepted_at) if user.privacy_policy_accepted else "no"}',
    ]
    lines.extend(_section('Profile', profile_lines))

    # Teaching assignments
    assignments = GroupTeacher.objects.filter(teacher=user).select_related('group', 'group__cohort')
    if assignments.exists():
        assign_lines = []
        for a in assignments:
            assign_lines.append(
                f'- **{a.group}** ({a.group.cohort}) — {a.get_role_display()}'
            )
        lines.extend(_section('Group teaching assignments', assign_lines))

    # Journal
    journals = JournalEntry.objects.filter(author=user).order_by('-entry_date')
    j_lines = []
    for e in journals:
        j_lines.extend([
            f'### {e.title}',
            f'*{_iso(e.entry_date)}* · Mood: {e.mood or "—"} · {e.get_visibility_display()}',
            '',
            _md_escape_block(e.content),
            '',
        ])
    lines.extend(_section(f'Journal entries ({journals.count()})', j_lines or ['_None_']))

    # Goals authored
    goals = Goal.objects.filter(author=user).prefetch_related('milestones').order_by('-created_at')
    g_lines = []
    for g in goals:
        g_lines.extend([
            f'### {g.title}',
            f'*{g.get_category_display()}* · Target: {_iso(g.target_date)} · {g.get_visibility_display()}',
            '',
            _md_escape_block(g.description),
            '',
        ])
        for m in g.milestones.all():
            g_lines.append(f'- Milestone: {m.title}')
        g_lines.append('')
    lines.extend(_section(f'Goals you created ({goals.count()})', g_lines or ['_None_']))

    # Goal enrollments
    goal_enrollments = (
        GoalEnrollment.objects.filter(student=user)
        .select_related('goal')
        .prefetch_related('goal__milestones', 'milestone_completions__milestone')
        .order_by('-enrolled_at')
    )
    ge_lines = []
    for en in goal_enrollments:
        done_ids = en.completed_milestone_ids()
        ge_lines.extend([
            f'### {en.goal.title}',
            f'Status: {en.get_status_display()} · Enrolled: {_iso(en.enrolled_at)}',
            '',
        ])
        for m in en.goal.milestones.all():
            mark = '✓' if m.pk in done_ids else '○'
            ge_lines.append(f'- {mark} {m.title}')
        ge_lines.append('')
    lines.extend(_section(f'Goal enrollments ({goal_enrollments.count()})', ge_lines or ['_None_']))

    # Staff-assigned goals created by user
    staff_goals = Goal.objects.filter(created_by=user, author__isnull=True).order_by('-created_at')
    if staff_goals.exists():
        sg_lines = [f'- {g.title} ({g.enrollments.count()} enrollments)' for g in staff_goals]
        lines.extend(_section(f'Goals you assigned to students ({staff_goals.count()})', sg_lines))

    # Reflections
    reflections = Reflection.objects.filter(author=user).order_by('-updated_at')
    r_lines = []
    for r in reflections:
        tags = ', '.join(r.tag_labels) or '—'
        r_lines.extend([
            f'### {r.title}',
            f'Tags: {tags} · {r.get_visibility_display()} · Updated: {_iso(r.updated_at)}',
            '',
            '**Expectations:**',
            '',
            _md_escape_block(r.expectations),
            '',
            '**Final reflection:**',
            '',
            _md_escape_block(r.final_reflection),
            '',
        ])
        wellbeing = [
            ('Energy', r.energy),
            ('Calmness', r.calmness),
            ('Engagement', r.engagement),
            ('Concentration', r.concentration),
            ('Sleep', r.sleep),
            ('Physical activity', r.physical_activity),
        ]
        wb = [f'- {label}: {v or "—"}' for label, v in wellbeing if v]
        if wb:
            r_lines.extend(['**Wellbeing:**', ''] + wb + [''])
    lines.extend(_section(f'Reflections ({reflections.count()})', r_lines or ['_None_']))

    # Habits
    habits = Habit.objects.filter(author=user).order_by('-created_at')
    h_lines = []
    for h in habits:
        h_lines.extend([
            f'### {h.title}',
            f'{h.get_status_display()} · {h.get_visibility_display()} · '
            f'Target: {h.target_minutes or "—"} min · {h.target_days_per_week} days/week',
            '',
            _md_escape_block(h.description),
            '',
        ])
        logs = HabitLog.objects.filter(habit=h).order_by('-date')[:90]
        for log in logs:
            h_lines.append(f'- {_iso(log.date)}: {log.get_status_display()}' + (f' — {log.note}' if log.note else ''))
        h_lines.append('')
    lines.extend(_section(f'Habits ({habits.count()})', h_lines or ['_None_']))

    # Personal / authored tasks
    personal_tasks = Task.objects.filter(assignee_user=user).order_by('-updated_at')
    authored_tasks = Task.objects.filter(author=user).order_by('-updated_at')
    pt_lines = []
    for t in personal_tasks:
        pt_lines.extend([
            f'### {t.title} (personal)',
            f'{t.get_status_display()} · {t.get_priority_display()} · Due: {_iso(t.due_date)} · '
            f'{t.get_visibility_display()}',
            '',
            _md_escape_block(t.description),
            '',
        ])
    for t in authored_tasks:
        if t.pk in {x.pk for x in personal_tasks}:
            continue
        pt_lines.extend([
            f'### {t.title} (authored)',
            f'{t.get_status_display()} · {t.get_priority_display()}',
            '',
            _md_escape_block(t.description),
            '',
        ])
    lines.extend(
        _section(
            f'Tasks — personal & authored ({personal_tasks.count() + authored_tasks.count()})',
            pt_lines or ['_None_'],
        )
    )

    # Task enrollments
    task_enrollments = (
        TaskEnrollment.objects.filter(student=user)
        .select_related('task')
        .prefetch_related('updates', 'comments', 'subtask_completions__subtask')
        .order_by('-enrolled_at')
    )
    te_lines = []
    for en in task_enrollments:
        te_lines.extend([
            f'### {en.task.title}',
            f'Status: {en.get_status_display()} · Enrolled: {_iso(en.enrolled_at)}',
            '',
            _md_escape_block(en.task.description),
            '',
        ])
        for u in en.updates.all():
            te_lines.append(f'- **{u.get_update_type_display()}** ({_iso(u.created_at)}): {_md_escape_block(u.text)}')
        for c in en.comments.filter(parent__isnull=True):
            te_lines.append(f'- Comment ({_iso(c.created_at)}): {_md_escape_block(c.text)}')
        te_lines.append('')
    lines.extend(_section(f'Task enrollments ({task_enrollments.count()})', te_lines or ['_None_']))

    # Tasks created for students
    assigned_tasks = Task.objects.filter(created_by=user, author__isnull=True).order_by('-created_at')
    if assigned_tasks.exists():
        at_lines = [f'- {t.title} ({t.enrollments.count()} students)' for t in assigned_tasks]
        lines.extend(_section(f'Tasks you assigned ({assigned_tasks.count()})', at_lines))

    # Task activity as author
    updates = TaskUpdate.objects.filter(author=user).select_related('enrollment__task')[:200]
    comments = TaskComment.objects.filter(author=user).select_related('enrollment__task')[:200]
    subtasks = Subtask.objects.filter(added_by=user).select_related('task')[:200]
    ta_lines = []
    for u in updates:
        ta_lines.append(f'- Update on **{u.enrollment.task.title}**: {_md_escape_block(u.text)[:200]}')
    for c in comments:
        ta_lines.append(f'- Comment on **{c.enrollment.task.title}**: {_md_escape_block(c.text)[:200]}')
    for s in subtasks:
        ta_lines.append(f'- Subtask on **{s.task.title}**: {s.title}')
    if ta_lines:
        lines.extend(_section('Task updates, comments & subtasks you wrote', ta_lines))

    # Workflows
    wf_enrollments = (
        WorkflowEnrollment.objects.filter(student=user)
        .select_related('workflow')
        .order_by('-enrolled_at')
    )
    we_lines = []
    for en in wf_enrollments:
        wf = en.workflow
        done = en.completed_step_ids()
        we_lines.append(f'### {wf.title}')
        we_lines.append(f'Enrolled: {_iso(en.enrolled_at)} · Progress: {en.progress_pct()}%')
        for step in wf.steps.all():
            mark = '✓' if step.pk in done else '○'
            we_lines.append(f'- {mark} {step.title}')
        we_lines.append('')
    lines.extend(_section(f'Workflow enrollments ({wf_enrollments.count()})', we_lines or ['_None_']))

    completions = StepCompletion.objects.filter(student=user).select_related('workflow', 'step')
    if completions.exists():
        sc_lines = [
            f'- {c.workflow.title} / {c.step.title} ({_iso(c.completed_at)})' for c in completions
        ]
        lines.extend(_section('Workflow step completions', sc_lines))

    created_workflows = Workflow.objects.filter(created_by=user).order_by('-created_at')
    if created_workflows.exists():
        cw_lines = [f'- {w.title} ({w.enrolled_count} enrolled)' for w in created_workflows]
        lines.extend(_section(f'Workflows you created ({created_workflows.count()})', cw_lines))

    # Group space
    posts = Post.objects.filter(author=user).select_related('group_space__group').order_by('-created_at')
    gp_lines = []
    for p in posts:
        gp_lines.extend([
            f'### Post in {p.group_space.group}',
            f'{_iso(p.created_at)}' + (' · pinned' if p.pinned else ''),
            '',
            _md_escape_block(p.body),
            '',
        ])
        if p.file:
            gp_lines.append(f'_Attached file: {p.file.name}_')
        if p.resource_label:
            gp_lines.append(f'_Resource label: {p.resource_label}_')
        gp_lines.append('')
    lines.extend(_section(f'Group posts ({posts.count()})', gp_lines or ['_None_']))

    g_comments = Comment.objects.filter(author=user).select_related('post__group_space__group')[:200]
    if g_comments.exists():
        gc_lines = [
            f'- On post in {c.post.group_space.group}: {_md_escape_block(c.body)[:160]}'
            for c in g_comments
        ]
        lines.extend(_section('Group comments you wrote', gc_lines))

    # Resources
    containers_owned = ResourceContainer.objects.filter(owner=user)
    containers_created = ResourceContainer.objects.filter(created_by=user).exclude(owner=user)
    items = ResourceItem.objects.filter(created_by=user).select_related('container')
    res_lines = []
    for c in containers_owned:
        res_lines.append(f'- Owned container: **{c.title}** ({c.get_container_type_display()})')
    for c in containers_created:
        res_lines.append(f'- Created container: **{c.title}** ({c.get_container_type_display()})')
    for i in items[:500]:
        res_lines.append(f'- Item **{i.title}** in {i.container.title}: {i.url}')
    lines.extend(_section('Resources', res_lines or ['_None_']))

    # Feedback given
    feedback_given = FeedbackEntry.objects.filter(author=user).select_related('content_type')[:500]
    fg_lines = []
    for fb in feedback_given:
        fg_lines.append(
            f'- On {fb.content_type.model} #{fb.object_id}: {_md_escape_block(fb.body)[:160]}'
        )
    lines.extend(_section(f'Feedback you left ({feedback_given.count()})', fg_lines or ['_None_']))

    # Feedback received (on user's content)
    received_lines = []
    for je in journals:
        for fb in FeedbackEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(JournalEntry),
            object_id=je.pk,
        ).select_related('author'):
            received_lines.append(f'- Journal "{je.title}" from {fb.author.display_name}: {fb.body[:120]}')
    for r in reflections:
        for fb in FeedbackEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(Reflection),
            object_id=r.pk,
        ).select_related('author'):
            received_lines.append(f'- Reflection "{r.title}" from {fb.author.display_name}: {fb.body[:120]}')
    for h in habits:
        for fb in FeedbackEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(Habit),
            object_id=h.pk,
        ).select_related('author'):
            received_lines.append(f'- Habit "{h.title}" from {fb.author.display_name}: {fb.body[:120]}')
    for en in goal_enrollments:
        for fb in FeedbackEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(GoalEnrollment),
            object_id=en.pk,
        ).select_related('author'):
            received_lines.append(
                f'- Goal "{en.goal.title}" from {fb.author.display_name}: {fb.body[:120]}'
            )
    for en in task_enrollments:
        for fb in FeedbackEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(TaskEnrollment),
            object_id=en.pk,
        ).select_related('author'):
            received_lines.append(
                f'- Task "{en.task.title}" from {fb.author.display_name}: {fb.body[:120]}'
            )
    lines.extend(_section('Feedback you received', received_lines or ['_None_']))

    # Notifications
    from .models import Notification

    notifs = Notification.objects.filter(recipient=user).order_by('-created_at')[:200]
    n_lines = [f'- [{_iso(n.created_at)}] {n.title}' + (f': {n.body[:80]}' if n.body else '') for n in notifs]
    lines.extend(_section(f'In-app notifications ({notifs.count()})', n_lines or ['_None_']))

    # Audit log (user actions)
    audit = user.audit_logs.order_by('-timestamp')[:100]
    if audit.exists():
        a_lines = [f'- {_iso(a.timestamp)} {a.method} {a.path}' for a in audit]
        lines.extend(_section('Recent audit log (your requests)', a_lines))

    return '\n'.join(lines).rstrip() + '\n'
