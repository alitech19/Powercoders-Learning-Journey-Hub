from django.contrib import admin

from .models import Goal, GoalComment, GoalEnrollment, Milestone, MilestoneCompletion


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


class GoalCommentInline(admin.TabularInline):
    model = GoalComment
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_by', 'category', 'visibility', 'target_date', 'created_at')
    list_filter = ('category', 'visibility')
    search_fields = ('title', 'author__display_name', 'author__email')
    autocomplete_fields = ('author', 'created_by')
    inlines = [MilestoneInline, GoalEnrollmentInline, GoalCommentInline]
    readonly_fields = ('created_at', 'updated_at')


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


@admin.register(GoalComment)
class GoalCommentAdmin(admin.ModelAdmin):
    list_display = ('goal', 'author', 'created_at')
    search_fields = ('body', 'goal__title', 'author__display_name')
    autocomplete_fields = ('goal', 'author')
