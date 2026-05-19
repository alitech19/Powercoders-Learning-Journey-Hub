from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'cohort', 'group', 'is_staff')
    list_filter = ('role', 'cohort', 'group', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    autocomplete_fields = ('cohort', 'group')
    fieldsets = UserAdmin.fieldsets + (
        ('Powerhub', {'fields': ('role', 'cohort', 'group')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Powerhub', {'fields': ('role', 'cohort', 'group')}),
    )
