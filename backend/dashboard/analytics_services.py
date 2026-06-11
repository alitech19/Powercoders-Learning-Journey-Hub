"""
Admin analytics — read-only aggregations used by the analytics dashboard.

All queries are intentionally simple and do not use window functions so
they remain portable across PostgreSQL versions.  Heavy calls are
cached at the view layer (1-hour TTL in production).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Max
from django.utils import timezone

from goals.models import GoalEnrollment
from group_space.models import Post
from habits.models import HabitLog
from journal.models import JournalEntry
from reflections.constants import TAG_WEEKLY
from reflections.models import Reflection

User = get_user_model()


# ── helpers ──────────────────────────────────────────────────────────────────


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _week_starts(weeks: int) -> list[date]:
    """Mondays for the last `weeks` weeks, oldest first."""
    monday = _monday_of(date.today())
    return [monday - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]


def _aware(d: date, end: bool = False) -> datetime:
    t = time.max if end else time.min
    return timezone.make_aware(datetime.combine(d, t))


def _student_ids() -> list[int]:
    return list(User.objects.filter(role=User.Role.STUDENT).values_list('pk', flat=True))


# ── weekly engagement ─────────────────────────────────────────────────────────


def weekly_engagement(weeks: int = 8) -> list[dict]:
    """
    For each of the last N weeks, count how many students had at least
    one activity (habit log, journal entry, reflection, or group post).

    Returns list of dicts: {week, active, total, pct}
    """
    student_ids = _student_ids()
    total = len(student_ids)
    if total == 0:
        return []

    rows = []
    for monday in _week_starts(weeks):
        sunday = monday + timedelta(days=6)

        active: set[int] = set()

        active |= set(
            HabitLog.objects.filter(
                habit__author_id__in=student_ids,
                date__range=(monday, sunday),
            ).values_list('habit__author_id', flat=True)
        )
        active |= set(
            JournalEntry.objects.filter(
                author_id__in=student_ids,
                created_at__range=(_aware(monday), _aware(sunday, end=True)),
            ).values_list('author_id', flat=True)
        )
        active |= set(
            Reflection.objects.filter(
                author_id__in=student_ids,
                created_at__range=(_aware(monday), _aware(sunday, end=True)),
            ).values_list('author_id', flat=True)
        )
        active |= set(
            Post.objects.filter(
                author_id__in=student_ids,
                created_at__range=(_aware(monday), _aware(sunday, end=True)),
            ).values_list('author_id', flat=True)
        )

        count = len(active)
        rows.append({
            'week': monday.strftime('%b %d').replace(' 0', ' '),
            'active': count,
            'total': total,
            'pct': round(count / total * 100) if total else 0,
        })

    return rows


# ── weekly reflection rate ────────────────────────────────────────────────────


def reflection_submission_rates(weeks: int = 8) -> list[dict]:
    """
    For each of the last N weeks, what % of students submitted their
    weekly reflection (based on final_reflection_at).

    Returns list of dicts: {week, submitted, total, pct}
    """
    student_ids = _student_ids()
    total = len(student_ids)
    if total == 0:
        return []

    rows = []
    for monday in _week_starts(weeks):
        next_monday = monday + timedelta(weeks=1)
        submitted = (
            Reflection.objects.filter(
                author_id__in=student_ids,
                tags__contains=[TAG_WEEKLY],
                final_reflection_at__range=(_aware(monday), _aware(next_monday)),
            )
            .values('author_id')
            .distinct()
            .count()
        )
        rows.append({
            'week': monday.strftime('%b %d').replace(' 0', ' '),
            'submitted': submitted,
            'total': total,
            'pct': round(submitted / total * 100) if total else 0,
        })

    return rows


# ── goal completion ───────────────────────────────────────────────────────────


def goal_completion_stats() -> dict:
    """
    Overall goal-enrollment status breakdown (all cohorts, all students).

    Returns dict: {total, completed, in_progress, not_started, abandoned, completion_pct}
    """
    qs = GoalEnrollment.objects.filter(student__role=User.Role.STUDENT)
    total = qs.count()
    if total == 0:
        return {
            'total': 0,
            'completed': 0,
            'in_progress': 0,
            'not_started': 0,
            'abandoned': 0,
            'completion_pct': 0,
        }

    by_status = {
        row['status']: row['cnt']
        for row in qs.values('status').annotate(cnt=Count('id'))
    }

    completed = by_status.get(GoalEnrollment.Status.COMPLETED, 0)
    return {
        'total': total,
        'completed': completed,
        'in_progress': by_status.get(GoalEnrollment.Status.IN_PROGRESS, 0),
        'not_started': by_status.get(GoalEnrollment.Status.NOT_STARTED, 0),
        'abandoned': by_status.get(GoalEnrollment.Status.ABANDONED, 0),
        'completion_pct': round(completed / total * 100) if total else 0,
    }


# ── at-risk students ──────────────────────────────────────────────────────────


def at_risk_students(days: int = 7) -> list[dict]:
    """
    Students with no activity in the last `days` days.
    Activity = habit log, journal entry, reflection, or group post.

    Returns list of dicts: {student, last_seen (date|None), days_inactive (int|None)}
    Sorted most-inactive first; capped at 20 rows.

    Query count: 5 fixed queries regardless of student count (was N×4 + 4).
      1. Fetch all students
      2. Max habit date per student   (HabitLog)
      3. Max journal date per student (JournalEntry)
      4. Max reflection date per student (Reflection)
      5. Max post date per student    (Post)
    """
    cutoff = date.today() - timedelta(days=days)

    students = list(
        User.objects.filter(role=User.Role.STUDENT)
        .select_related('group', 'cohort')
        .order_by('display_name')
    )
    if not students:
        return []

    student_ids = [s.pk for s in students]

    # ── 4 bulk queries: last activity date per student across all time ────────
    # HabitLog.date is a DateField — Max() returns a date directly.
    habit_lasts: dict[int, date] = dict(
        HabitLog.objects
        .filter(habit__author_id__in=student_ids)
        .values('habit__author_id')
        .annotate(last=Max('date'))
        .values_list('habit__author_id', 'last')
    )

    # created_at is a DateTimeField — Max() returns a datetime; convert to date.
    journal_lasts: dict[int, date] = {
        pk: dt.date()
        for pk, dt in JournalEntry.objects
        .filter(author_id__in=student_ids)
        .values('author_id')
        .annotate(last=Max('created_at'))
        .values_list('author_id', 'last')
        if dt is not None
    }

    reflection_lasts: dict[int, date] = {
        pk: dt.date()
        for pk, dt in Reflection.objects
        .filter(author_id__in=student_ids)
        .values('author_id')
        .annotate(last=Max('created_at'))
        .values_list('author_id', 'last')
        if dt is not None
    }

    post_lasts: dict[int, date] = {
        pk: dt.date()
        for pk, dt in Post.objects
        .filter(author_id__in=student_ids)
        .values('author_id')
        .annotate(last=Max('created_at'))
        .values_list('author_id', 'last')
        if dt is not None
    }

    # ── determine who is recently active (no DB queries) ─────────────────────
    recently_active: set[int] = set()
    for source in (habit_lasts, journal_lasts, reflection_lasts, post_lasts):
        for pk, last_date in source.items():
            if last_date >= cutoff:
                recently_active.add(pk)

    # ── build at-risk list using dict lookups — zero extra DB queries ─────────
    today = date.today()
    at_risk = []

    for student in students:
        pk = student.pk
        if pk in recently_active:
            continue

        candidate_dates: list[date] = [
            d for d in (
                habit_lasts.get(pk),
                journal_lasts.get(pk),
                reflection_lasts.get(pk),
                post_lasts.get(pk),
            )
            if d is not None
        ]

        if candidate_dates:
            last_seen = max(candidate_dates)
            days_inactive = (today - last_seen).days
        else:
            last_seen = None
            days_inactive = None

        at_risk.append({
            'student': student,
            'last_seen': last_seen,
            'days_inactive': days_inactive,
        })

    # Sort: never-active first, then most days inactive
    at_risk.sort(
        key=lambda x: x['days_inactive'] if x['days_inactive'] is not None else 99999,
        reverse=True,
    )
    return at_risk[:20]


# ── cohort comparison ─────────────────────────────────────────────────────────


def cohort_comparison() -> list[dict]:
    """
    Per-cohort engagement stats for the current week.

    Returns list of dicts per cohort:
    {name, status, students, reflection_rate, habit_rate, goal_completion_rate}
    """
    from cohorts.models import Cohort

    cohorts = Cohort.objects.order_by('name')
    week_ago = date.today() - timedelta(days=7)
    week_ago_dt = _aware(week_ago)

    rows = []
    for cohort in cohorts:
        student_ids = list(
            User.objects.filter(role=User.Role.STUDENT, cohort=cohort)
            .values_list('pk', flat=True)
        )
        total = len(student_ids)
        if total == 0:
            continue

        reflection_submitters = (
            Reflection.objects.filter(
                author_id__in=student_ids,
                tags__contains=[TAG_WEEKLY],
                final_reflection_at__gte=week_ago_dt,
            )
            .values('author_id')
            .distinct()
            .count()
        )

        habit_active = (
            HabitLog.objects.filter(
                habit__author_id__in=student_ids,
                date__gte=week_ago,
            )
            .values('habit__author_id')
            .distinct()
            .count()
        )

        total_enrollments = GoalEnrollment.objects.filter(
            student_id__in=student_ids,
        ).count()
        completed_enrollments = GoalEnrollment.objects.filter(
            student_id__in=student_ids,
            status=GoalEnrollment.Status.COMPLETED,
        ).count()

        rows.append({
            'name': cohort.name,
            'status': cohort.status,
            'students': total,
            'reflection_rate': round(reflection_submitters / total * 100) if total else 0,
            'habit_rate': round(habit_active / total * 100) if total else 0,
            'goal_completion_rate': (
                round(completed_enrollments / total_enrollments * 100)
                if total_enrollments
                else 0
            ),
        })

    return rows
