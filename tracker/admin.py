from django.contrib import admin

from .models import Task, TaskComment, TaskUpdate


def _is_private_personal(task):
    return (
        task.scope_type == Task.ScopeType.USER
        and task.visibility == Task.Visibility.PRIVATE
    )


TASK_METADATA_FIELDS = (
    'scope_type', 'user', 'group', 'cohort', 'assignee', 'created_by',
    'visibility', 'status', 'priority', 'due_date',
    'created_at', 'updated_at', 'completed_at',
)

TASK_ALL_FIELDS = (
    'title', 'description', 'scope_type', 'user', 'group', 'cohort',
    'parent', 'assignee', 'created_by', 'visibility', 'status', 'priority',
    'due_date', 'created_at', 'updated_at', 'completed_at',
)


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
        'display_title',
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
        'user__display_name',
        'user__email',
        'assignee__display_name',
        'assignee__email',
        'group__name',
        'cohort__name',
    )
    autocomplete_fields = ('user', 'group', 'cohort', 'parent', 'assignee', 'created_by')
    inlines = [TaskInline, TaskUpdateInline, TaskCommentInline]
    readonly_fields = ('created_at', 'updated_at', 'completed_at')

    @admin.display(description='Title')
    def display_title(self, obj):
        if _is_private_personal(obj):
            return 'Private task - content hidden'
        return obj.title

    def get_fields(self, request, obj=None):
        if obj and _is_private_personal(obj):
            return TASK_METADATA_FIELDS
        return TASK_ALL_FIELDS

    def get_readonly_fields(self, request, obj=None):
        if obj and _is_private_personal(obj):
            return TASK_METADATA_FIELDS
        return self.readonly_fields

    def get_inlines(self, request, obj=None):
        if obj and _is_private_personal(obj):
            return []
        return self.inlines

    def has_change_permission(self, request, obj=None):
        if obj and _is_private_personal(obj):
            return False
        return super().has_change_permission(request, obj)


@admin.register(TaskUpdate)
class TaskUpdateAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'update_type', 'display_text', 'created_at')
    list_filter = ('update_type',)
    search_fields = ('task__user__display_name', 'task__user__email', 'author__display_name', 'author__email')
    autocomplete_fields = ('task', 'author')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Text')
    def display_text(self, obj):
        if _is_private_personal(obj.task):
            return 'Hidden'
        return obj.text[:80]

    def get_fields(self, request, obj=None):
        if obj and _is_private_personal(obj.task):
            return ('task', 'author', 'update_type', 'created_at', 'updated_at')
        return ('task', 'author', 'update_type', 'text', 'created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        if obj and _is_private_personal(obj.task):
            return ('task', 'author', 'update_type', 'created_at', 'updated_at')
        return self.readonly_fields

    def has_change_permission(self, request, obj=None):
        if obj and _is_private_personal(obj.task):
            return False
        return super().has_change_permission(request, obj)


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'parent', 'display_text', 'created_at')
    list_filter = (('parent', admin.EmptyFieldListFilter),)
    search_fields = ('task__user__display_name', 'task__user__email', 'author__display_name', 'author__email')
    autocomplete_fields = ('task', 'author', 'parent')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Text')
    def display_text(self, obj):
        if _is_private_personal(obj.task):
            return 'Hidden'
        return obj.text[:80]

    def get_fields(self, request, obj=None):
        if obj and _is_private_personal(obj.task):
            return ('task', 'parent', 'author', 'created_at', 'updated_at')
        return ('task', 'parent', 'author', 'text', 'created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        if obj and _is_private_personal(obj.task):
            return ('task', 'parent', 'author', 'created_at', 'updated_at')
        return self.readonly_fields

    def has_change_permission(self, request, obj=None):
        if obj and _is_private_personal(obj.task):
            return False
        return super().has_change_permission(request, obj)
