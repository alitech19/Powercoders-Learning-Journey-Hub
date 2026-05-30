"""Task enrollment feedback hooks for the generic feedback app."""

from accounts.models import User
from cohorts.permissions import user_is_staff

from .models import Task, TaskEnrollment
from .permissions import can_view_task, is_staff_assigned


def _teacher_supervises_enrollment(user, enrollment):
    from cohorts.permissions import get_teacher_group_ids

    student = enrollment.student
    if not student or not student.group_id:
        return False
    return student.group_id in get_teacher_group_ids(user)


def can_view_enrollment_feedback(user, enrollment):
    task = enrollment.task
    if user.role == User.Role.STUDENT:
        if enrollment.student_id != user.pk:
            return False
        if is_staff_assigned(task) and task.visibility == Task.Visibility.PRIVATE:
            return False
        return True

    if not can_view_task(user, task):
        return False
    if user_is_staff(user):
        return _teacher_supervises_enrollment(user, enrollment)
    return False


def can_add_enrollment_feedback(user, enrollment):
    task = enrollment.task
    if not user_is_staff(user):
        return False
    if task.visibility != Task.Visibility.SHARED:
        return False
    return can_view_enrollment_feedback(user, enrollment)


def enrollment_feedback_context(enrollment, viewer):
    task = enrollment.task
    placeholder = 'Leave feedback for this student…'
    if viewer.pk != enrollment.student_id:
        placeholder = f'Leave feedback for {enrollment.student.display_name}…'
    return {
        'visibility_shared': task.visibility == Task.Visibility.SHARED,
        'feedback_placeholder': placeholder,
    }


def register_task_feedback_handlers():
    from feedback.registry import FeedbackHandlers, register

    register(
        TaskEnrollment,
        FeedbackHandlers(
            can_view=can_view_enrollment_feedback,
            can_add=can_add_enrollment_feedback,
            extra_context=enrollment_feedback_context,
        ),
    )
