from django.contrib import admin

from .models import Task, TaskComment, TaskUpdate


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


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'scope_type',
        'user',
        'group',
        'cohort',
        'assignee',
        'visibility',
        'status',
        'priority',
        'due_date',
        'updated_at',
    )
    list_filter = ('scope_type', 'visibility', 'status', 'priority', 'group', 'cohort')
    search_fields = (
        'title',
        'description',
        'user__display_name',
        'user__email',
        'assignee__display_name',
        'assignee__email',
        'group__name',
        'cohort__name',
    )
    autocomplete_fields = ('user', 'group', 'cohort', 'parent', 'assignee', 'created_by')
    inlines = [TaskInline, TaskUpdateInline, TaskCommentInline]


@admin.register(TaskUpdate)
class TaskUpdateAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'update_type', 'created_at')
    list_filter = ('update_type',)
    search_fields = ('text', 'task__title', 'author__display_name', 'author__email')
    autocomplete_fields = ('task', 'author')


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'parent', 'created_at')
    list_filter = (('parent', admin.EmptyFieldListFilter),)
    search_fields = ('text', 'task__title', 'author__display_name', 'author__email', 'parent__text')
    autocomplete_fields = ('task', 'author', 'parent')
    fields = ('task', 'parent', 'author', 'text')
