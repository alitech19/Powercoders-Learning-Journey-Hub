from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models

from config.input_limits import (
    DESCRIPTION_MAX_LENGTH,
    STEP_DESCRIPTION_MAX_LENGTH,
    TITLE_MAX_LENGTH,
)


class Workflow(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Private'

    class ProgressMode(models.TextChoices):
        SHARED = 'shared', 'Shared'
        INDIVIDUAL = 'individual', 'Individual'

    class AssigneeType(models.TextChoices):
        COHORT = 'cohort', 'Cohort'
        GROUP = 'group', 'Group'

    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    description = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(DESCRIPTION_MAX_LENGTH)],
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    progress_mode = models.CharField(max_length=20, choices=ProgressMode.choices)
    assignee_type = models.CharField(max_length=20, choices=AssigneeType.choices)
    assignee_cohort = models.ForeignKey(
        'cohorts.Cohort',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='workflows',
    )
    assignee_group = models.ForeignKey(
        'cohorts.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='workflows',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_workflows',
    )
    resource_container = models.ForeignKey(
        'resources.ResourceContainer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflows',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_private(self):
        return self.visibility == self.Visibility.PRIVATE

    @property
    def is_shared(self):
        return self.progress_mode == self.ProgressMode.SHARED

    @property
    def step_count(self):
        return self.steps.count()

    @property
    def enrolled_count(self):
        return self.enrollments.count()

    def get_assignee_label(self):
        if self.assignee_type == self.AssigneeType.GROUP and self.assignee_group_id:
            return str(self.assignee_group)
        if self.assignee_type == self.AssigneeType.COHORT and self.assignee_cohort_id:
            return self.assignee_cohort.name
        return '—'

    def clean(self):
        errors = {}
        if self.assignee_type == self.AssigneeType.COHORT:
            if not self.assignee_cohort_id:
                errors['assignee_cohort'] = 'Cohort is required for cohort assignment.'
            if self.assignee_group_id:
                errors['assignee_group'] = 'Group must be empty for cohort assignment.'
        elif self.assignee_type == self.AssigneeType.GROUP:
            if not self.assignee_group_id:
                errors['assignee_group'] = 'Group is required for group assignment.'
            if self.assignee_cohort_id:
                errors['assignee_cohort'] = 'Cohort must be empty for group assignment.'
        if errors:
            raise ValidationError(errors)


class WorkflowStep(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='steps')
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    description = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(STEP_DESCRIPTION_MAX_LENGTH)],
    )
    order = models.PositiveSmallIntegerField(default=0)
    requires_previous = models.BooleanField(
        default=True,
        help_text='Student must complete the previous step before unlocking this one.',
    )

    class Meta:
        ordering = ['order', 'pk']

    def __str__(self):
        return f'{self.workflow.title} — Step {self.order}: {self.title}'


class WorkflowEnrollment(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workflow_enrollments',
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['workflow', 'student'], name='unique_workflow_enrollment'),
        ]
        ordering = ['-enrolled_at']

    def __str__(self):
        return f'{self.student} → {self.workflow}'

    def completed_step_ids(self):
        return set(
            StepCompletion.objects.filter(
                workflow=self.workflow,
                student=self.student,
            ).values_list('step_id', flat=True)
        )

    def progress_pct(self):
        total = self.workflow.steps.count()
        if not total:
            return 0
        done = StepCompletion.objects.filter(workflow=self.workflow, student=self.student).count()
        return round(done / total * 100)


class StepCompletion(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='completions')
    step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE, related_name='completions')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='workflow_step_completions',
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='workflow_steps_marked_done',
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['workflow', 'step'],
                condition=models.Q(student__isnull=True),
                name='unique_shared_step_completion',
            ),
            models.UniqueConstraint(
                fields=['workflow', 'step', 'student'],
                condition=models.Q(student__isnull=False),
                name='unique_individual_step_completion',
            ),
        ]
        ordering = ['completed_at']

    def __str__(self):
        who = self.student.display_name if self.student_id else 'shared'
        return f'{who} ✓ {self.step.title}'
