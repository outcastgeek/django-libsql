"""App configuration for analytics."""

from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Analytics app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "analytics"

    def ready(self):
        """Start real-time tracker when app is ready."""
        from .tracker import tracker

        tracker.start()
