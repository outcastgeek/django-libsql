"""Admin configuration for blog app."""

from django.contrib import admin
from .models import Author, Category, Tag, Post, Comment, PostView


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["user", "website", "post_count", "total_views"]
    search_fields = ["user__username", "user__email", "bio"]

    def post_count(self, obj):
        return obj.post_count

    post_count.short_description = "Posts"

    def total_views(self, obj):
        return obj.total_views

    total_views.short_description = "Total Views"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "post_count"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "description"]

    def post_count(self, obj):
        return obj.posts.filter(status="published").count()

    post_count.short_description = "Published Posts"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "post_count"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]

    def post_count(self, obj):
        return obj.posts.filter(status="published").count()

    post_count.short_description = "Posts"


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ["author_name", "content", "is_approved", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "author",
        "category",
        "status",
        "published_date",
        "view_count",
        "comment_count",
        "created_at",
    ]
    list_filter = ["status", "category", "author", "created_at", "published_date"]
    search_fields = ["title", "content", "excerpt"]
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "created_at"
    filter_horizontal = ["tags"]
    inlines = [CommentInline]

    fieldsets = (
        (None, {"fields": ("title", "slug", "author", "category", "tags")}),
        ("Content", {"fields": ("content", "excerpt", "featured_image_url")}),
        ("Publishing", {"fields": ("status", "published_date", "allow_comments")}),
        ("Stats", {"fields": ("view_count",), "classes": ("collapse",)}),
    )

    def comment_count(self, obj):
        return obj.comments.filter(is_approved=True).count()

    comment_count.short_description = "Comments"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["author_name", "post", "is_approved", "parent", "created_at"]
    list_filter = ["is_approved", "created_at"]
    search_fields = ["author_name", "author_email", "content"]
    date_hierarchy = "created_at"
    actions = ["approve_comments", "reject_comments"]

    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)

    approve_comments.short_description = "Approve selected comments"

    def reject_comments(self, request, queryset):
        queryset.update(is_approved=False)

    reject_comments.short_description = "Reject selected comments"


@admin.register(PostView)
class PostViewAdmin(admin.ModelAdmin):
    list_display = ["post", "ip_address", "timestamp", "referrer"]
    list_filter = ["timestamp"]
    search_fields = ["post__title", "ip_address", "referrer"]
    date_hierarchy = "timestamp"
    readonly_fields = ["post", "ip_address", "user_agent", "referrer", "timestamp"]
