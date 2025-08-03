"""App configuration for todo."""

from django.apps import AppConfig


class TodoConfig(AppConfig):
    """Todo app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "todo"
