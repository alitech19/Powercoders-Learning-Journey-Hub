from django.contrib import admin

from .models import Comment, GroupSpace, Post, ProjectSpace, ProjectSpaceMembership, SpaceSlackChannel


class ProjectSpaceMembershipInline(admin.TabularInline):
    model = ProjectSpaceMembership
    extra = 0
    raw_id_fields = ('user', 'added_by')


@admin.register(ProjectSpace)
class ProjectSpaceAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'is_archived', 'created_at')
    list_filter = ('is_archived',)
    search_fields = ('title', 'description', 'created_by__email')
    raw_id_fields = ('created_by',)
    inlines = [ProjectSpaceMembershipInline]
    actions = ['mark_archived', 'mark_unarchived']

    @admin.action(description='Archive selected project spaces')
    def mark_archived(self, request, queryset):
        queryset.update(is_archived=True)

    @admin.action(description='Unarchive selected project spaces')
    def mark_unarchived(self, request, queryset):
        queryset.update(is_archived=False)


@admin.register(SpaceSlackChannel)
class SpaceSlackChannelAdmin(admin.ModelAdmin):
    list_display = ('slack_channel_id', 'group_space', 'project_space', 'is_enabled', 'updated_at')
    list_filter = ('is_enabled',)
    raw_id_fields = ('group_space', 'project_space')


@admin.register(GroupSpace)
class GroupSpaceAdmin(admin.ModelAdmin):
    list_display = ('group', 'created_at')
    search_fields = ('group__name', 'group__cohort__name')
    raw_id_fields = ('group',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'group_space', 'project_space', 'author', 'resource_label', 'pinned', 'snapshot_kind', 'created_at')
    list_filter = ('pinned', 'snapshot_kind', 'created_at')
    search_fields = ('body', 'resource_label', 'author__display_name')
    raw_id_fields = ('group_space', 'project_space', 'author')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'created_at')
    search_fields = ('body', 'author__display_name')
    raw_id_fields = ('post', 'author')
