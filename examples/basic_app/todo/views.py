"""Views for the todo app."""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.utils import timezone
from django.db import OperationalError
from .models import Todo, Category


def index(request):
    """Main todo list view."""
    todos = Todo.objects.select_related("category").prefetch_related("attachments")
    categories = Category.objects.annotate(todo_count=Count("todos"))

    # Filter by category if specified
    category_id = request.GET.get("category")
    if category_id:
        todos = todos.filter(category_id=category_id)

    # Filter by completion status
    status = request.GET.get("status")
    if status == "completed":
        todos = todos.filter(completed=True)
    elif status == "pending":
        todos = todos.filter(completed=False)

    # Search functionality
    search = request.GET.get("search")
    if search:
        todos = todos.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    context = {
        "todos": todos,
        "categories": categories,
        "current_category": category_id,
        "current_status": status,
        "search_query": search,
        "stats": {
            "total": Todo.objects.count(),
            "completed": Todo.objects.filter(completed=True).count(),
            "pending": Todo.objects.filter(completed=False).count(),
            "overdue": Todo.objects.filter(
                completed=False, due_date__lt=timezone.now()
            ).count(),
        },
    }
    return render(request, "todo/index.html", context)


@require_http_methods(["POST"])
def add_todo(request):
    """Add a new todo via AJAX."""
    title = request.POST.get("title")
    if not title:
        return JsonResponse({"error": "Title is required"}, status=400)

    todo = Todo.objects.create(
        title=title,
        description=request.POST.get("description", ""),
        priority=request.POST.get("priority", "medium"),
        category_id=request.POST.get("category") or None,
        due_date=request.POST.get("due_date") or None,
    )

    return JsonResponse(
        {
            "id": todo.id,
            "title": todo.title,
            "priority": todo.priority,
            "completed": todo.completed,
            "created_at": todo.created_at.isoformat(),
        }
    )


@require_http_methods(["POST"])
def toggle_todo(request, todo_id):
    """Toggle todo completion status."""
    todo = get_object_or_404(Todo, id=todo_id)
    todo.completed = not todo.completed
    todo.save()

    return JsonResponse(
        {
            "id": todo.id,
            "completed": todo.completed,
            "updated_at": todo.updated_at.isoformat(),
        }
    )


@require_http_methods(["DELETE"])
def delete_todo(request, todo_id):
    """Delete a todo."""
    todo = get_object_or_404(Todo, id=todo_id)
    todo.delete()

    return JsonResponse({"message": "Todo deleted successfully"})


def categories(request):
    """Category management view."""
    categories = Category.objects.annotate(
        todo_count=Count("todos"),
        completed_count=Count("todos", filter=Q(todos__completed=True)),
    )

    return render(
        request,
        "todo/categories.html",
        {
            "categories": categories,
        },
    )
