from django.contrib import admin

from .models import Comment, GroupSpace, Post


@admin.register(GroupSpace)
class GroupSpaceAdmin(admin.ModelAdmin):
    list_display = ('group', 'created_at')
    search_fields = ('group__name', 'group__cohort__name')
    raw_id_fields = ('group',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('group_space', 'author', 'resource_label', 'pinned', 'snapshot_kind', 'created_at')
    list_filter = ('pinned', 'snapshot_kind', 'created_at')
    search_fields = ('body', 'resource_label', 'author__display_name')
    raw_id_fields = ('group_space', 'author')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'created_at')
    search_fields = ('body', 'author__display_name')
    raw_id_fields = ('post', 'author')
