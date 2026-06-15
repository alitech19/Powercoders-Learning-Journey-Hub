from django.contrib import admin

from .models import IntegratedModule
from .module_access import invalidate_module_cache


@admin.register(IntegratedModule)
class IntegratedModuleAdmin(admin.ModelAdmin):
    list_display = ('label', 'slug', 'is_enabled', 'updated_at', 'updated_by')
    list_editable = ('is_enabled',)
    list_filter = ('is_enabled',)
    search_fields = ('slug', 'label')
    readonly_fields = ('slug', 'label', 'updated_at', 'updated_by')

    def has_module_permission(self, request):
        return request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        invalidate_module_cache()
