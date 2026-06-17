from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group as AuthGroup

from .models import (
    AuditLog,
    Notification,
    NotificationDeliveryLog,
    NotificationDigestItem,
    SlackIntegration,
    User,
    UserNotificationSettings,
)

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
        ('Site profile', {'fields': ('display_name', 'avatar_updated_at')}),
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


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'recipient', 'title', 'is_read')
    list_filter = ('is_read',)
    search_fields = ('title', 'recipient__email', 'recipient__display_name')
    readonly_fields = ('created_at',)


@admin.register(NotificationDeliveryLog)
class NotificationDeliveryLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'recipient', 'channel', 'status', 'event_key')
    list_filter = ('channel', 'status')
    search_fields = ('event_key', 'recipient__email', 'recipient__display_name')
    readonly_fields = (
        'event_key',
        'recipient',
        'channel',
        'status',
        'provider_message_id',
        'error_message',
        'created_at',
        'sent_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(NotificationDigestItem)
class NotificationDigestItemAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'recipient', 'channel', 'digest_bucket', 'status', 'event_key')
    list_filter = ('channel', 'digest_bucket', 'status')
    search_fields = ('event_key', 'recipient__email', 'recipient__display_name')
    readonly_fields = (
        'event_key',
        'recipient',
        'channel',
        'digest_bucket',
        'scheduled_for',
        'created_at',
        'provider_message_id',
        'error_message',
        'sent_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserNotificationSettings)
class UserNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_enabled', 'slack_enabled', 'digest_mode', 'updated_at')
    search_fields = ('user__email', 'user__display_name')
    autocomplete_fields = ('user',)


@admin.register(SlackIntegration)
class SlackIntegrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'slack_team_id', 'slack_user_id', 'is_active', 'connected_at')
    search_fields = ('user__email', 'user__display_name', 'slack_user_id')
    readonly_fields = ('connected_at', 'disconnected_at', 'last_error')
    autocomplete_fields = ('user',)


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
