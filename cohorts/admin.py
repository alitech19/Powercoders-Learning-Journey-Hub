from django.contrib import admin

from .models import Cohort, Group, GroupTeacher


class GroupInline(admin.TabularInline):
    model = Group
    extra = 0


class GroupTeacherInline(admin.TabularInline):
    model = GroupTeacher
    extra = 0
    autocomplete_fields = ('teacher',)


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name',)
    inlines = [GroupInline]


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'cohort', 'created_at')
    list_filter = ('cohort',)
    search_fields = ('name', 'cohort__name')
    autocomplete_fields = ('cohort',)
    inlines = [GroupTeacherInline]


@admin.register(GroupTeacher)
class GroupTeacherAdmin(admin.ModelAdmin):
    list_display = ('group', 'teacher', 'role', 'created_at')
    list_filter = ('role', 'group__cohort')
    search_fields = ('group__name', 'teacher__username', 'teacher__email')
    autocomplete_fields = ('group', 'teacher')
