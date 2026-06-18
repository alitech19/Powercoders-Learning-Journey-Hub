from django.contrib import admin

from .models import (
    Subtask,
    SubtaskEnrollment,
    Task,
    TaskComment,
    TaskEnrollment,
    TaskUpdate,
)


class SubtaskInline(admin.TabularInline):
    model = Subtask
    extra = 0
    fields = ('order', 'title', 'priority', 'due_date', 'added_by')


class SubtaskEnrollmentInline(admin.TabularInline):
    model = SubtaskEnrollment
    extra = 0
    fields = ('subtask', 'status', 'completed_at')
    readonly_fields = ('completed_at',)
    autocomplete_fields = ('subtask',)


class TaskEnrollmentInline(admin.TabularInline):
    model = TaskEnrollment
    extra = 0
    fields = ('student', 'status', 'completed_at', 'enrolled_at')
    readonly_fields = ('enrolled_at',)
    autocomplete_fields = ('student',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'author',
        'assignee_type',
        'progress_mode',
        'visibility',
        'scheduled_publish_at',
        'status',
        'priority',
        'created_at',
    )
    list_filter = ('assignee_type', 'progress_mode', 'visibility', 'status', 'priority')
    search_fields = ('title', 'author__display_name', 'author__email')
    autocomplete_fields = (
        'author',
        'created_by',
        'assignee_user',
        'assignee_group',
        'assignee_cohort',
        'resource_container',
    )
    inlines = [SubtaskInline, TaskEnrollmentInline]
    readonly_fields = ('created_at', 'updated_at', 'completed_at', 'scheduled_publish_task_id')
    fieldsets = (
        (None, {'fields': ('title', 'description', 'status', 'priority', 'due_date', 'visibility')}),
        (
            'Assignment',
            {
                'fields': (
                    'author',
                    'created_by',
                    'assignee_type',
                    'progress_mode',
                    'assignee_user',
                    'assignee_group',
                    'assignee_cohort',
                ),
            },
        ),
        (
            'Collaboration',
            {'fields': ('allow_updates', 'allow_comments', 'allow_subtasks')},
        ),
        ('Materials', {'fields': ('resource_container',)}),
        (
            'Scheduled publication',
            {'fields': ('scheduled_publish_at', 'scheduled_publish_task_id')},
        ),
        ('Timestamps', {'fields': ('created_at', 'updated_at', 'completed_at')}),
    )


@admin.register(TaskEnrollment)
class TaskEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('task', 'student', 'status', 'completed_at', 'enrolled_at')
    list_filter = ('status',)
    search_fields = ('task__title', 'student__display_name', 'student__email')
    autocomplete_fields = ('task', 'student')
    inlines = [SubtaskEnrollmentInline]


@admin.register(Subtask)
class SubtaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'task', 'priority', 'due_date', 'order', 'added_by')
    search_fields = ('title', 'task__title')
    autocomplete_fields = ('task', 'added_by')


@admin.register(SubtaskEnrollment)
class SubtaskEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'subtask', 'status', 'completed_at')
    list_filter = ('status',)
    autocomplete_fields = ('enrollment', 'subtask')


@admin.register(TaskUpdate)
class TaskUpdateAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'author', 'update_type', 'created_at')
    list_filter = ('update_type',)
    autocomplete_fields = ('enrollment', 'author')


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'author', 'parent', 'created_at')
    search_fields = ('text', 'author__display_name', 'enrollment__task__title')
    autocomplete_fields = ('enrollment', 'author', 'parent')
