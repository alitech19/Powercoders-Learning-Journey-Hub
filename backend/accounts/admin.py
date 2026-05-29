from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group as AuthGroup

from .models import AuditLog, User

try:
    admin.site.unregister(AuthGroup)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    ordering = ('email',)
    list_display = (
        'email',
        'display_name',
        'role',
        'cohort',
        'group',
        'privacy_policy_accepted',
        'must_change_password',
        'is_staff',
        'is_active',
    )
    list_filter = (
        'role',
        'cohort',
        'group',
        'privacy_policy_accepted',
        'must_change_password',
        'welcome_seen',
        'is_staff',
        'is_superuser',
        'is_active',
    )
    search_fields = ('email', 'display_name')
    autocomplete_fields = ('cohort', 'group')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Site profile', {'fields': ('display_name', 'avatar')}),
        (
            'PowerHUB',
            {
                'fields': (
                    'role',
                    'cohort',
                    'group',
                    'email_notifications_enabled',
                    'privacy_policy_accepted',
                    'privacy_policy_accepted_at',
                    'welcome_seen',
                    'must_change_password',
                ),
            },
        ),
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
                    'cohort',
                    'group',
                ),
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if obj and obj.role != User.Role.STUDENT:
            for index, (title, options) in enumerate(fieldsets):
                if title == 'PowerHUB':
                    options = {**options, 'fields': (
                        'role',
                        'email_notifications_enabled',
                        'privacy_policy_accepted',
                        'privacy_policy_accepted_at',
                        'welcome_seen',
                        'must_change_password',
                    )}
                    fieldsets[index] = (title, options)
                    break
        return fieldsets


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'method', 'path', 'user_email', 'ip_address')
    list_filter = ('method',)
    search_fields = ('path', 'user_email')
    readonly_fields = (
        'user',
        'user_email',
        'method',
        'path',
        'ip_address',
        'timestamp',
    )
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
