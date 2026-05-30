"""Goal access control — hardcoded business rules."""

from django.db.models import Q

from accounts.models import User
from cohorts.permissions import get_teacher_group_ids, user_is_admin, user_is_staff, user_is_teacher

from .models import Goal, GoalEnrollment


def is_staff_assigned(goal):
    return goal.author_id is None


def get_enrollment_for_user(user, goal):
    if not user.is_authenticated:
        return None
    return goal.enrollments.filter(student=user).first()


def _teacher_supervises_student(user, student):
    if not student or not student.group_id:
        return False
    return student.group_id in get_teacher_group_ids(user)


def _staff_private_draft():
    return Q(author__isnull=True) & Q(visibility=Goal.Visibility.PRIVATE)


def can_view_goal(user, goal):
    if not user.is_authenticated:
        return False

    if user.role == User.Role.STUDENT:
        enrollment = get_enrollment_for_user(user, goal)
        if not enrollment:
            return False
        if is_staff_assigned(goal) and goal.visibility == Goal.Visibility.PRIVATE:
            return False
        return True

    if user_is_admin(user):
        if goal.visibility == Goal.Visibility.SHARED:
            return True
        return is_staff_assigned(goal) and goal.visibility == Goal.Visibility.PRIVATE

    if user_is_teacher(user):
        in_scope = goal.enrollments.filter(
            student__group_id__in=get_teacher_group_ids(user),
        ).exists()
        if not in_scope:
            return False
        if goal.visibility == Goal.Visibility.PRIVATE:
            return is_staff_assigned(goal)
        return True

    return False


def can_manage_goal(user, goal):
    """Edit, delete — template-level actions for staff-assigned goals."""
    if not can_view_goal(user, goal):
        return False
    if user_is_admin(user):
        return True
    if is_staff_assigned(goal):
        if user_is_teacher(user):
            return goal.enrollments.filter(
                student__group_id__in=get_teacher_group_ids(user),
            ).exists()
        return False
    return goal.author_id == user.pk


def can_edit_goal(user, goal):
    return can_manage_goal(user, goal)


def can_delete_goal(user, goal):
    return can_manage_goal(user, goal)


def can_toggle_milestone(user, enrollment):
    if enrollment.status == GoalEnrollment.Status.COMPLETED:
        return False
    goal = enrollment.goal
    if not can_view_goal(user, goal):
        return False
    if user_is_admin(user):
        return True
    return enrollment.student_id == user.pk


def can_mark_achieved(user, enrollment):
    if enrollment.status == GoalEnrollment.Status.COMPLETED:
        return False
    if not enrollment.all_milestones_complete:
        return False
    if not can_view_goal(user, enrollment.goal):
        return False
    if user_is_admin(user):
        return True
    return enrollment.student_id == user.pk


def can_reactivate_enrollment(user, enrollment):
    if enrollment.status != GoalEnrollment.Status.COMPLETED:
        return False
    goal = enrollment.goal
    if user_is_admin(user):
        return can_view_goal(user, goal)
    if enrollment.student_id == user.pk and not is_staff_assigned(goal):
        return True
    if user_is_teacher(user) and is_staff_assigned(goal):
        return _teacher_supervises_student(user, enrollment.student)
    return False


def can_add_feedback(user, goal):
    if not user_is_staff(user):
        return False
    if goal.visibility != Goal.Visibility.SHARED:
        return False
    return can_view_goal(user, goal)


def can_create_goals(user):
    return user.is_authenticated and (
        user.role == User.Role.STUDENT or user_is_staff(user)
    )


def get_visible_goals_for_user(user):
    qs = (
        Goal.objects.select_related('author', 'created_by')
        .prefetch_related('milestones', 'enrollments__student')
    )

    if user.role == User.Role.STUDENT:
        return qs.filter(enrollments__student=user).exclude(_staff_private_draft()).distinct()

    if user_is_teacher(user):
        group_ids = get_teacher_group_ids(user)
        if not group_ids:
            return qs.none()
        in_scope = Q(enrollments__student__group_id__in=group_ids)
        return qs.filter(
            in_scope & (Q(visibility=Goal.Visibility.SHARED) | _staff_private_draft())
        ).distinct()

    if user_is_admin(user):
        return qs.filter(
            Q(visibility=Goal.Visibility.SHARED) | _staff_private_draft()
        ).distinct()

    return qs.none()


def get_visible_enrollments_for_user(user, *, goal=None):
    qs = GoalEnrollment.objects.select_related('goal', 'student', 'student__group')
    if goal is not None:
        if not can_view_goal(user, goal):
            return qs.none()
        qs = qs.filter(goal=goal)
    if user.role == User.Role.STUDENT:
        return qs.filter(student=user)
    if user_is_teacher(user):
        group_ids = get_teacher_group_ids(user)
        return qs.filter(student__group_id__in=group_ids)
    if user_is_admin(user):
        return qs
    return qs.none()
