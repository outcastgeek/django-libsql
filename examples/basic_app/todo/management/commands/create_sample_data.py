"""Create sample data for todo app."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from todo.models import Category, Todo, TodoAttachment


class Command(BaseCommand):
    help = "Creates sample data for the todo app"

    def handle(self, *args, **options):
        self.stdout.write("Creating sample data...")

        # Create categories
        categories = [
            {"name": "Work", "description": "Work-related tasks", "color": "#007bff"},
            {"name": "Personal", "description": "Personal tasks", "color": "#28a745"},
            {"name": "Shopping", "description": "Shopping lists", "color": "#ffc107"},
            {"name": "Health", "description": "Health and fitness", "color": "#dc3545"},
            {
                "name": "Learning",
                "description": "Educational goals",
                "color": "#6610f2",
            },
        ]

        created_categories = []
        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                name=cat_data["name"],
                defaults={
                    "description": cat_data["description"],
                    "color": cat_data["color"],
                },
            )
            created_categories.append(category)
            if created:
                self.stdout.write(f"Created category: {category.name}")

        # Create todos
        todo_templates = [
            {
                "title": "Complete project documentation",
                "priority": "high",
                "category": 0,
            },
            {"title": "Review pull requests", "priority": "medium", "category": 0},
            {"title": "Update dependencies", "priority": "low", "category": 0},
            {"title": "Team meeting at 3 PM", "priority": "urgent", "category": 0},
            {"title": "Buy groceries", "priority": "medium", "category": 2},
            {
                "title": "Call dentist for appointment",
                "priority": "high",
                "category": 3,
            },
            {"title": "Finish online course", "priority": "medium", "category": 4},
            {"title": "Plan weekend trip", "priority": "low", "category": 1},
            {"title": "Pay utility bills", "priority": "urgent", "category": 1},
            {"title": "Gym workout", "priority": "medium", "category": 3},
        ]

        for i, todo_data in enumerate(todo_templates):
            # Add some variation to due dates
            due_date = None
            if random.random() > 0.3:  # 70% have due dates
                days_offset = random.randint(-2, 7)
                due_date = timezone.now() + timedelta(days=days_offset)

            # Some todos are already completed
            completed = random.random() < 0.3  # 30% completed

            todo = Todo.objects.create(
                title=todo_data["title"],
                description=f"Description for: {todo_data['title']}",
                category=created_categories[todo_data["category"]],
                priority=todo_data["priority"],
                completed=completed,
                due_date=due_date,
            )

            # Add attachments to some todos
            if random.random() < 0.2:  # 20% have attachments
                TodoAttachment.objects.create(
                    todo=todo,
                    file_name=f"document_{i}.pdf",
                    file_size=random.randint(100000, 5000000),
                    mime_type="application/pdf",
                )

            self.stdout.write(f"Created todo: {todo.title}")

        # Summary
        total_todos = Todo.objects.count()
        completed_todos = Todo.objects.filter(completed=True).count()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully created sample data:\n"
                f"- {len(created_categories)} categories\n"
                f"- {total_todos} todos ({completed_todos} completed)\n"
                f"- {TodoAttachment.objects.count()} attachments"
            )
        )
