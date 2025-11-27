from django.contrib import admin
from .models import Post, Comment


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('id', 'author', 'created_at', 'updated_at')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'comment_count')
    list_filter = ('created_at', 'author')
    search_fields = ('title', 'description', 'author__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [CommentInline]

    def comment_count(self, obj):
        return obj.comment_count
    comment_count.short_description = 'Comments'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'post', 'author', 'created_at')
    list_filter = ('created_at', 'author')
    search_fields = ('text', 'author__username', 'post__title')
    readonly_fields = ('id', 'created_at', 'updated_at')
