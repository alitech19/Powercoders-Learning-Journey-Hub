from django.contrib import admin

from .models import FeedbackEntry


@admin.register(FeedbackEntry)
class FeedbackEntryAdmin(admin.ModelAdmin):
    list_display = ('content_type', 'object_id', 'author', 'body_preview', 'created_at')
    list_filter = ('content_type', 'created_at')
    search_fields = ('body', 'author__display_name', 'author__email')
    readonly_fields = ('content_type', 'object_id', 'author', 'created_at')
    autocomplete_fields = ('author',)

    @admin.display(description='Body')
    def body_preview(self, obj):
        return obj.body[:80] + ('…' if len(obj.body) > 80 else '')
