from django.contrib import admin

from .models import (
    DriveUploadLog,
    GoogleAccountConnection,
    GoogleDriveFolder,
    GoogleWorkspaceStorageConfig,
)


@admin.register(GoogleWorkspaceStorageConfig)
class GoogleWorkspaceStorageConfigAdmin(admin.ModelAdmin):
    list_display = (
        'is_enabled',
        'shared_drive_name',
        'service_account_email',
        'student_oauth_enabled',
        'last_health_ok',
        'updated_at',
    )
    readonly_fields = (
        'service_account_email',
        'last_health_check_at',
        'last_health_ok',
        'last_error',
        'updated_at',
        'updated_by',
    )
    fieldsets = (
        ('General', {'fields': ('is_enabled',)}),
        (
            'Org Shared drive (staff)',
            {
                'fields': (
                    'shared_drive_id',
                    'shared_drive_name',
                    'shared_root_folder_id',
                    'root_folder_name',
                    'service_account_json_encrypted',
                    'service_account_email',
                ),
            },
        ),
        (
            'Students (My Drive)',
            {
                'fields': (
                    'student_oauth_enabled',
                    'oauth_client_id',
                    'oauth_client_secret_encrypted',
                    'oauth_redirect_uri',
                    'workspace_hosted_domain',
                ),
            },
        ),
        (
            'Diagnostics',
            {
                'fields': (
                    'last_health_check_at',
                    'last_health_ok',
                    'last_error',
                    'updated_at',
                    'updated_by',
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        return not GoogleWorkspaceStorageConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(GoogleAccountConnection)
class GoogleAccountConnectionAdmin(admin.ModelAdmin):
    list_display = (
        'google_email',
        'user',
        'connected_at',
        'disconnected_at',
        'last_error',
    )
    search_fields = ('google_email', 'user__email', 'user__display_name')
    readonly_fields = (
        'google_subject',
        'google_email',
        'connected_at',
        'disconnected_at',
        'root_folder_id',
        'last_error',
    )


@admin.register(GoogleDriveFolder)
class GoogleDriveFolderAdmin(admin.ModelAdmin):
    list_display = (
        'drive_path',
        'storage_backend',
        'folder_kind',
        'group',
        'user',
        'drive_folder_id',
    )
    list_filter = ('storage_backend', 'folder_kind')
    search_fields = ('drive_path', 'drive_folder_id')


@admin.register(DriveUploadLog)
class DriveUploadLogAdmin(admin.ModelAdmin):
    list_display = (
        'post',
        'user',
        'storage_backend',
        'status',
        'duration_ms',
        'created_at',
    )
    list_filter = ('status', 'storage_backend')
    readonly_fields = (
        'post',
        'user',
        'storage_backend',
        'status',
        'duration_ms',
        'error_code',
        'error_message',
        'created_at',
    )
