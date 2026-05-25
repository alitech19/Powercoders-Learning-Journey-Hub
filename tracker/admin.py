from django.contrib import admin
from django.db.models import Q

from .models import Task, TaskComment, TaskUpdate


TASK_ALL_FIELDS = (
    'title', 'description', 'assignee_type', 'assignee_user', 'assignee_group', 'assignee_cohort',
    'parent', 'created_by', 'visibility', 'status', 'priority',
    'due_date', 'created_at', 'updated_at', 'completed_at',
)


class TaskInline(admin.TabularInline):
    model = Task
    fk_name = 'parent'
    extra = 0
    fields = ('title', 'status', 'priority', 'visibility')
    show_change_link = True


class TaskUpdateInline(admin.TabularInline):
    model = TaskUpdate
    extra = 0
    autocomplete_fields = ('author',)


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    autocomplete_fields = ('author',)


def _visible_task_q(user):
    """Public tasks + private tasks created by this user."""
    return Q(visibility=Task.Visibility.PUBLIC) | Q(created_by=user)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'assignee_type',
        'assignee_user',
        'assignee_group',
        'assignee_cohort',
        'created_by',
        'visibility',
        'status',
        'priority',
        'due_date',
        'updated_at',
    )
    list_filter = ('assignee_type', 'visibility', 'status', 'priority', 'assignee_group', 'assignee_cohort')
    search_fields = (
        'title',
        'assignee_user__display_name',
        'assignee_user__email',
        'created_by__display_name',
        'created_by__email',
        'assignee_group__name',
        'assignee_cohort__name',
    )
    autocomplete_fields = ('assignee_user', 'assignee_group', 'assignee_cohort', 'parent', 'created_by')
    inlines = [TaskInline, TaskUpdateInline, TaskCommentInline]
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    fields = TASK_ALL_FIELDS

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(_visible_task_q(request.user))

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.parent_id:
            return self.readonly_fields + ('visibility', 'assignee_type', 'assignee_user', 'assignee_group', 'assignee_cohort')
        return self.readonly_fields


@admin.register(TaskUpdate)
class TaskUpdateAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'update_type', 'display_text', 'created_at')
    list_filter = ('update_type',)
    search_fields = ('task__title', 'author__display_name', 'author__email')
    autocomplete_fields = ('task', 'author')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Text')
    def display_text(self, obj):
        return obj.text[:80]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(
            Q(task__visibility=Task.Visibility.PUBLIC) | Q(task__created_by=request.user)
        )


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'parent', 'display_text', 'created_at')
    list_filter = (('parent', admin.EmptyFieldListFilter),)
    search_fields = ('task__title', 'author__display_name', 'author__email')
    autocomplete_fields = ('task', 'author', 'parent')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Text')
    def display_text(self, obj):
        return obj.text[:80]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(
            Q(task__visibility=Task.Visibility.PUBLIC) | Q(task__created_by=request.user)
        )
