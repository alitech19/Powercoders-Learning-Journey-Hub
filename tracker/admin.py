from django.contrib import admin

from .models import Task, TaskBoard, TaskComment, TaskUpdate


class TaskInline(admin.TabularInline):
    model = Task
    fk_name = 'parent'
    extra = 0
    fields = ('title', 'status', 'priority', 'visibility', 'assignee')
    autocomplete_fields = ('assignee',)
    show_change_link = True


class TaskUpdateInline(admin.TabularInline):
    model = TaskUpdate
    extra = 0
    autocomplete_fields = ('author',)


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    autocomplete_fields = ('author',)


@admin.register(TaskBoard)
class TaskBoardAdmin(admin.ModelAdmin):
    list_display = ('title', 'scope_type', 'user', 'group', 'cohort', 'created_by', 'updated_at')
    list_filter = ('scope_type',)
    search_fields = ('title', 'user__username', 'group__name', 'cohort__name')
    autocomplete_fields = ('user', 'group', 'cohort', 'created_by')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'board',
        'parent',
        'status',
        'priority',
        'visibility',
        'assignee',
        'due_date',
        'updated_at',
    )
    list_filter = ('status', 'priority', 'visibility', 'board__scope_type')
    search_fields = ('title', 'description', 'assignee__username')
    autocomplete_fields = ('board', 'parent', 'assignee', 'created_by')
    inlines = [TaskInline, TaskUpdateInline, TaskCommentInline]


@admin.register(TaskUpdate)
class TaskUpdateAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'update_type', 'created_at')
    list_filter = ('update_type',)
    search_fields = ('text', 'task__title', 'author__username')
    autocomplete_fields = ('task', 'author')


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'created_at')
    search_fields = ('text', 'task__title', 'author__username')
    autocomplete_fields = ('task', 'author')
