from django.contrib import admin

from .models import Feedback, Goal, WeeklyReflection


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'student', 'visibility', 'status',
        'time_bound', 'achieved_at', 'updated_at',
    )
    list_filter = ('visibility', 'status')
    search_fields = (
        'title', 'student__display_name', 'student__email',
    )
    autocomplete_fields = ('student',)
    readonly_fields = ('created_at', 'updated_at', 'achieved_at')


@admin.register(WeeklyReflection)
class WeeklyReflectionAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'week_start', 'week_end', 'created_at',
    )
    list_filter = ('week_start',)
    search_fields = (
        'student__display_name', 'student__email',
    )
    autocomplete_fields = ('student',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        'author', 'student', 'content_type', 'object_id',
        'display_message', 'created_at',
    )
    search_fields = (
        'author__display_name', 'author__email',
        'student__display_name', 'student__email',
    )
    autocomplete_fields = ('author', 'student')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Message')
    def display_message(self, obj):
        return obj.message[:80]
