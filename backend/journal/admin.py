from django.contrib import admin

from .models import JournalEntry


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'entry_date', 'visibility', 'word_count_display', 'updated_at')
    list_filter = ('visibility', 'entry_date')
    search_fields = ('title', 'author__display_name', 'author__email', 'tags')
    autocomplete_fields = ('author',)
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Words')
    def word_count_display(self, obj):
        return obj.word_count
