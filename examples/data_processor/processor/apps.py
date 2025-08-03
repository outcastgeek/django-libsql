"""App configuration for processor."""

from django.apps import AppConfig


class ProcessorConfig(AppConfig):
    """Processor app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "processor"
