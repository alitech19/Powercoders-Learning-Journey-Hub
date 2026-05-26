from django.contrib import admin

from .models import DailyJournalEntry, Feedback, Goal, GoalSubgoal, Habit, HabitLog, WellbeingCheckIn, WeeklyReflection


class GoalSubgoalInline(admin.TabularInline):
    model = GoalSubgoal
    extra = 0
    readonly_fields = ('created_at', 'updated_at', 'completed_at')


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'student', 'created_by', 'visibility', 'status',
        'progress_percent', 'target_date', 'achieved_at', 'updated_at',
    )
    list_filter = ('visibility', 'status')
    search_fields = (
        'title', 'student__display_name', 'student__email',
    )
    autocomplete_fields = ('student', 'created_by')
    readonly_fields = ('created_at', 'updated_at', 'achieved_at')
    inlines = [GoalSubgoalInline]


@admin.register(GoalSubgoal)
class GoalSubgoalAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'goal', 'status', 'order',
        'created_by', 'completed_at', 'created_at',
    )
    list_filter = ('status',)
    search_fields = ('title', 'goal__title')
    autocomplete_fields = ('goal', 'created_by')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')


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


@admin.register(DailyJournalEntry)
class DailyJournalEntryAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'entry_date', 'display_content', 'created_at',
    )
    list_filter = ('entry_date',)
    search_fields = (
        'student__display_name', 'student__email',
    )
    autocomplete_fields = ('student',)
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Content')
    def display_content(self, obj):
        return obj.content[:80]


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'student', 'status', 'target_minutes',
        'target_days_per_week', 'completed_weekly_streak',
        'completed_at', 'updated_at',
    )
    list_filter = ('status',)
    search_fields = (
        'title', 'student__display_name', 'student__email',
    )
    autocomplete_fields = ('student',)
    readonly_fields = ('created_at', 'updated_at', 'completed_at')


@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = (
        'habit', 'date', 'status', 'display_note', 'created_at',
    )
    list_filter = ('status', 'date')
    search_fields = (
        'habit__title',
    )
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Note')
    def display_note(self, obj):
        return obj.note[:80] if obj.note else ''


@admin.register(WellbeingCheckIn)
class WellbeingCheckInAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'check_date', 'energy', 'calmness',
        'engagement', 'concentration', 'sleep',
        'physical_activity', 'created_at',
    )
    list_filter = ('check_date',)
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
