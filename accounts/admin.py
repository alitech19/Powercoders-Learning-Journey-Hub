from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    ordering = ('email',)
    list_display = ('email', 'display_name', 'role', 'cohort', 'group', 'is_staff')
    list_filter = ('role', 'cohort', 'group', 'is_staff', 'is_superuser')
    search_fields = ('email', 'display_name')
    autocomplete_fields = ('cohort', 'group')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Site profile', {'fields': ('display_name', 'avatar')}),
        ('Powerhub', {'fields': ('role', 'cohort', 'group')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'display_name',
                    'password1',
                    'password2',
                    'role',
                    'cohort',
                    'group',
                ),
            },
        ),
    )
