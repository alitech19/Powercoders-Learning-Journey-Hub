from django.contrib import admin

from .models import ResourceContainer, ResourceItem


class ResourceItemInline(admin.TabularInline):
    model = ResourceItem
    extra = 0
    readonly_fields = ('source_post', 'created_by', 'created_at')


@admin.register(ResourceContainer)
class ResourceContainerAdmin(admin.ModelAdmin):
    list_display = ('title', 'container_type', 'group', 'owner', 'is_system', 'updated_at')
    list_filter = ('container_type', 'is_system')
    search_fields = ('title', 'group__name', 'owner__email')
    inlines = [ResourceItemInline]


@admin.register(ResourceItem)
class ResourceItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'container', 'url', 'source_post', 'updated_at')
    list_filter = ('container__container_type',)
    search_fields = ('title', 'url')
