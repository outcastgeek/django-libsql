"""Admin configuration for todo app."""

from django.contrib import admin
from .models import Todo, Category, TodoAttachment


class TodoAttachmentInline(admin.TabularInline):
    """Inline admin for todo attachments."""

    model = TodoAttachment
    extra = 0
    readonly_fields = ["uploaded_at"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for categories."""

    list_display = ["name", "color", "todo_count", "created_at"]
    search_fields = ["name", "description"]

    def todo_count(self, obj):
        """Get number of todos in category."""
        return obj.todos.count()

    todo_count.short_description = "Todos"


@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    """Admin for todos."""

    list_display = [
        "title",
        "category",
        "priority",
        "completed",
        "due_date",
        "created_at",
    ]
    list_filter = ["completed", "priority", "category", "created_at"]
    search_fields = ["title", "description"]
    date_hierarchy = "created_at"
    inlines = [TodoAttachmentInline]

    fieldsets = (
        (None, {"fields": ("title", "description", "category", "priority")}),
        ("Status", {"fields": ("completed", "due_date")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    readonly_fields = ["created_at", "updated_at"]
