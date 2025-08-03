"""Models for real-time analytics with Turso sync."""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import json
from datetime import timedelta


class Website(models.Model):
    """Website being tracked."""

    domain = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=100)
    tracking_id = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PageView(models.Model):
    """Individual page view event."""

    website = models.ForeignKey(
        Website, on_delete=models.CASCADE, related_name="pageviews"
    )
    session_id = models.CharField(max_length=100, db_index=True)
    page_path = models.CharField(max_length=500)
    page_title = models.CharField(max_length=200, blank=True)

    # User info
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()

    # Referrer info
    referrer_url = models.URLField(blank=True)
    referrer_domain = models.CharField(max_length=255, blank=True, db_index=True)

    # Device info
    device_type = models.CharField(max_length=20)  # desktop, mobile, tablet
    browser = models.CharField(max_length=50)
    os = models.CharField(max_length=50)

    # Location info (from IP)
    country = models.CharField(max_length=2, blank=True)  # ISO code
    city = models.CharField(max_length=100, blank=True)

    # Performance metrics
    page_load_time = models.FloatField(null=True, blank=True)  # seconds

    timestamp = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["website", "-timestamp"]),
            models.Index(fields=["session_id", "-timestamp"]),
            models.Index(fields=["page_path", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.page_path} at {self.timestamp}"


class Event(models.Model):
    """Custom events (clicks, form submissions, etc)."""

    EVENT_TYPES = [
        ("click", "Click"),
        ("form_submit", "Form Submit"),
        ("download", "Download"),
        ("video_play", "Video Play"),
        ("scroll", "Scroll"),
        ("custom", "Custom"),
    ]

    website = models.ForeignKey(
        Website, on_delete=models.CASCADE, related_name="events"
    )
    session_id = models.CharField(max_length=100, db_index=True)
    pageview = models.ForeignKey(
        PageView, on_delete=models.CASCADE, null=True, related_name="events"
    )

    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, db_index=True)
    event_name = models.CharField(max_length=100)
    event_value = models.CharField(max_length=255, blank=True)
    event_data = models.JSONField(default=dict)

    timestamp = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["website", "event_type", "-timestamp"]),
            models.Index(fields=["session_id", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.event_name} ({self.event_type}) at {self.timestamp}"


class Session(models.Model):
    """User session aggregation."""

    website = models.ForeignKey(
        Website, on_delete=models.CASCADE, related_name="sessions"
    )
    session_id = models.CharField(max_length=100, unique=True)

    # Session info
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)

    # Metrics
    pageview_count = models.IntegerField(default=0)
    event_count = models.IntegerField(default=0)
    bounce = models.BooleanField(default=False)

    # User info (from first pageview)
    ip_address = models.GenericIPAddressField()
    country = models.CharField(max_length=2, blank=True)
    device_type = models.CharField(max_length=20)
    browser = models.CharField(max_length=50)

    # Entry/exit pages
    entry_page = models.CharField(max_length=500)
    exit_page = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["website", "-started_at"]),
            models.Index(fields=["session_id"]),
        ]

    def __str__(self):
        return f"Session {self.session_id}"

    def calculate_duration(self):
        """Calculate session duration from pageviews."""
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at).total_seconds()
        return 0


class RealtimeVisitor(models.Model):
    """Track visitors currently on site (last 5 minutes)."""

    website = models.ForeignKey(
        Website, on_delete=models.CASCADE, related_name="realtime_visitors"
    )
    session_id = models.CharField(max_length=100)
    page_path = models.CharField(max_length=500)

    ip_address = models.GenericIPAddressField()
    country = models.CharField(max_length=2, blank=True)
    device_type = models.CharField(max_length=20)

    last_seen = models.DateTimeField(db_index=True)

    class Meta:
        unique_together = [["website", "session_id"]]
        indexes = [
            models.Index(fields=["website", "-last_seen"]),
        ]

    @classmethod
    def cleanup_old(cls, minutes=5):
        """Remove visitors not seen in the last N minutes."""
        cutoff = timezone.now() - timedelta(minutes=minutes)
        cls.objects.filter(last_seen__lt=cutoff).delete()


class HourlyStats(models.Model):
    """Hourly aggregated statistics."""

    website = models.ForeignKey(
        Website, on_delete=models.CASCADE, related_name="hourly_stats"
    )
    hour = models.DateTimeField(db_index=True)

    # Metrics
    pageviews = models.IntegerField(default=0)
    unique_visitors = models.IntegerField(default=0)
    sessions = models.IntegerField(default=0)
    bounces = models.IntegerField(default=0)
    events = models.IntegerField(default=0)

    # Performance
    avg_page_load_time = models.FloatField(null=True, blank=True)
    avg_session_duration = models.FloatField(null=True, blank=True)

    # Top data (stored as JSON)
    top_pages = models.JSONField(default=list)  # [{path, views}, ...]
    top_referrers = models.JSONField(default=list)  # [{domain, count}, ...]
    device_breakdown = models.JSONField(default=dict)  # {desktop: N, mobile: N, ...}

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["website", "hour"]]
        ordering = ["-hour"]
        indexes = [
            models.Index(fields=["website", "-hour"]),
        ]

    def __str__(self):
        return f"{self.website.name} - {self.hour}"


class DailyStats(models.Model):
    """Daily aggregated statistics."""

    website = models.ForeignKey(
        Website, on_delete=models.CASCADE, related_name="daily_stats"
    )
    date = models.DateField(db_index=True)

    # Metrics
    pageviews = models.IntegerField(default=0)
    unique_visitors = models.IntegerField(default=0)
    sessions = models.IntegerField(default=0)
    bounces = models.IntegerField(default=0)
    bounce_rate = models.FloatField(null=True, blank=True)  # percentage
    events = models.IntegerField(default=0)

    # Performance
    avg_page_load_time = models.FloatField(null=True, blank=True)
    avg_session_duration = models.FloatField(null=True, blank=True)
    pages_per_session = models.FloatField(null=True, blank=True)

    # Growth (compared to previous day)
    pageviews_growth = models.FloatField(null=True, blank=True)  # percentage
    visitors_growth = models.FloatField(null=True, blank=True)  # percentage

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["website", "date"]]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["website", "-date"]),
        ]

    def __str__(self):
        return f"{self.website.name} - {self.date}"
