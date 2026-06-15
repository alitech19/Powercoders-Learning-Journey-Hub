from django.contrib import admin

from .models import BugReport, BugReportMessage


class BugReportMessageInline(admin.TabularInline):
    model = BugReportMessage
    extra = 0
    readonly_fields = ('author', 'body', 'is_staff_reply', 'created_at')


@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'reporter', 'assigned_to', 'page_path', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('description', 'page_url', 'reporter__email', 'reporter__display_name')
    readonly_fields = ('reporter', 'page_url', 'page_path', 'created_at', 'updated_at')
    inlines = [BugReportMessageInline]


@admin.register(BugReportMessage)
class BugReportMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'report', 'author', 'is_staff_reply', 'created_at')
    list_filter = ('is_staff_reply',)
    search_fields = ('body', 'author__email')
