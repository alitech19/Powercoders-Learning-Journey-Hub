from django.contrib import admin

from .models import Habit, HabitLog


class HabitLogInline(admin.TabularInline):
    model = HabitLog
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'author', 'status', 'visibility',
        'target_days_per_week', 'completed_weekly_streak', 'updated_at',
    )
    list_filter = ('status', 'visibility')
    search_fields = ('title', 'author__display_name', 'author__email')
    autocomplete_fields = ('author',)
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    inlines = [HabitLogInline]


@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ('habit', 'date', 'status', 'created_at')
    list_filter = ('status', 'date')
    search_fields = ('habit__title', 'habit__author__display_name')
    autocomplete_fields = ('habit',)
    readonly_fields = ('created_at', 'updated_at')
