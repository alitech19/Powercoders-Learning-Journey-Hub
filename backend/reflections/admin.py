from django.contrib import admin

from .models import Reflection


@admin.register(Reflection)
class ReflectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'visibility', 'wellbeing_filled_count', 'updated_at')
    list_filter = ('visibility',)
    search_fields = ('title', 'author__display_name', 'author__email', 'custom_label')
    autocomplete_fields = ('author',)
    readonly_fields = ('created_at', 'updated_at')
