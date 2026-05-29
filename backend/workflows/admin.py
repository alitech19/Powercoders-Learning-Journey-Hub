from django.contrib import admin
from django.db.models import Q

from .models import StepCompletion, Workflow, WorkflowEnrollment, WorkflowStep


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 0
    fields = ('order', 'title', 'requires_previous')
    ordering = ('order',)


class WorkflowEnrollmentInline(admin.TabularInline):
    model = WorkflowEnrollment
    extra = 0
    autocomplete_fields = ('student',)


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'progress_mode',
        'assignee_type',
        'assignee_cohort',
        'assignee_group',
        'visibility',
        'created_by',
        'created_at',
    )
    list_filter = ('progress_mode', 'assignee_type', 'visibility', 'assignee_cohort')
    search_fields = ('title', 'created_by__display_name', 'created_by__email')
    autocomplete_fields = ('created_by', 'assignee_cohort', 'assignee_group')
    inlines = [WorkflowStepInline, WorkflowEnrollmentInline]
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or getattr(request.user, 'role', None) == 'admin':
            return qs
        return qs.filter(
            Q(visibility=Workflow.Visibility.PUBLIC)
            | Q(created_by=request.user)
        )


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = ('title', 'workflow', 'order', 'requires_previous')
    search_fields = ('title', 'workflow__title')
    autocomplete_fields = ('workflow',)


@admin.register(WorkflowEnrollment)
class WorkflowEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'student', 'enrolled_at')
    autocomplete_fields = ('workflow', 'student')


@admin.register(StepCompletion)
class StepCompletionAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'step', 'student', 'completed_by', 'completed_at')
    autocomplete_fields = ('workflow', 'step', 'student', 'completed_by')
