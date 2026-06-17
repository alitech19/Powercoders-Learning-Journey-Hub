from django.contrib import admin

from .models import Goal, GoalEnrollment, Milestone, MilestoneCompletion


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0
    fields = ('order', 'title')


class GoalEnrollmentInline(admin.TabularInline):
    model = GoalEnrollment
    extra = 0
    fields = ('student', 'status', 'achieved_at', 'enrolled_at')
    readonly_fields = ('enrolled_at',)
    autocomplete_fields = ('student',)


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'author',
        'created_by',
        'category',
        'visibility',
        'scheduled_publish_at',
        'target_date',
        'created_at',
    )
    list_filter = ('category', 'visibility')
    search_fields = ('title', 'author__display_name', 'author__email')
    autocomplete_fields = ('author', 'created_by', 'resource_container')
    inlines = [MilestoneInline, GoalEnrollmentInline]
    readonly_fields = ('created_at', 'updated_at', 'scheduled_publish_task_id')
    fieldsets = (
        (None, {'fields': ('title', 'description', 'category', 'target_date', 'visibility')}),
        (
            'Assignment',
            {'fields': ('author', 'created_by')},
        ),
        ('Materials', {'fields': ('resource_container',)}),
        (
            'Scheduled publication',
            {'fields': ('scheduled_publish_at', 'scheduled_publish_task_id')},
        ),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(GoalEnrollment)
class GoalEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('goal', 'student', 'status', 'achieved_at', 'enrolled_at')
    list_filter = ('status',)
    search_fields = ('goal__title', 'student__display_name', 'student__email')
    autocomplete_fields = ('goal', 'student')


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('title', 'goal', 'order')
    search_fields = ('title', 'goal__title')
    autocomplete_fields = ('goal',)


@admin.register(MilestoneCompletion)
class MilestoneCompletionAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'milestone', 'completed_at')
    autocomplete_fields = ('enrollment', 'milestone')
