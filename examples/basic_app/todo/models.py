"""Todo models demonstrating basic Django ORM with libSQL."""

from django.db import models
from django.utils import timezone


class Category(models.Model):
    """Category for organizing todos."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#007bff")  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Todo(models.Model):
    """Todo item model."""

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="todos"
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )
    completed = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "-created_at"]
        indexes = [
            models.Index(fields=["completed", "priority"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self):
        return self.title

    def is_overdue(self):
        """Check if the todo is overdue."""
        if self.due_date and not self.completed:
            return timezone.now() > self.due_date
        return False


class TodoAttachment(models.Model):
    """Attachment for todo items."""

    todo = models.ForeignKey(Todo, on_delete=models.CASCADE, related_name="attachments")
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # in bytes
    mime_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name} ({self.todo.title})"
