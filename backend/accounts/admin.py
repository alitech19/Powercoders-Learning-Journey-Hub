from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group as AuthGroup

from .models import User

try:
    admin.site.unregister(AuthGroup)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    ordering = ('email',)
    list_display = ('email', 'display_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'display_name')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Site profile', {'fields': ('display_name', 'avatar')}),
        ('PowerHUB', {'fields': ('role', 'email_notifications_enabled')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
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
                ),
            },
        ),
    )
