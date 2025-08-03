"""Models for concurrent data processing with libSQL."""

from django.db import models
from django.utils import timezone
import json


class DataSource(models.Model):
    """Source of data to be processed."""

    name = models.CharField(max_length=100, unique=True)
    url = models.URLField(blank=True)
    api_key = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_fetched = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class ProcessingJob(models.Model):
    """Job for processing data in batches."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    name = models.CharField(max_length=200)
    data_source = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name="jobs"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Job configuration
    config = models.JSONField(default=dict)
    batch_size = models.PositiveIntegerField(default=100)
    num_workers = models.PositiveIntegerField(default=4)

    # Progress tracking
    total_items = models.PositiveIntegerField(default=0)
    processed_items = models.PositiveIntegerField(default=0)
    failed_items = models.PositiveIntegerField(default=0)

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Results
    result_summary = models.JSONField(default=dict)
    error_log = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["data_source", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def progress_percentage(self):
        if self.total_items == 0:
            return 0
        return int((self.processed_items / self.total_items) * 100)

    @property
    def duration(self):
        if not self.started_at:
            return None
        end_time = self.completed_at or timezone.now()
        return (end_time - self.started_at).total_seconds()

    @property
    def items_per_second(self):
        if not self.duration or self.duration == 0:
            return 0
        return self.processed_items / self.duration


class DataItem(models.Model):
    """Individual item to be processed."""

    job = models.ForeignKey(
        ProcessingJob, on_delete=models.CASCADE, related_name="items"
    )
    external_id = models.CharField(max_length=100, db_index=True)
    data = models.JSONField()

    # Processing status
    is_processed = models.BooleanField(default=False)
    is_failed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    # Results
    processed_data = models.JSONField(null=True, blank=True)
    processing_time = models.FloatField(null=True, blank=True)  # in seconds

    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["job", "external_id"]]
        indexes = [
            models.Index(fields=["job", "is_processed"]),
            models.Index(fields=["job", "is_failed"]),
        ]

    def __str__(self):
        return f"Item {self.external_id} for {self.job.name}"


class ProcessingMetrics(models.Model):
    """Metrics for monitoring processing performance."""

    job = models.ForeignKey(
        ProcessingJob, on_delete=models.CASCADE, related_name="metrics"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    # Performance metrics
    items_per_second = models.FloatField()
    active_workers = models.PositiveIntegerField()
    queue_size = models.PositiveIntegerField()

    # Resource usage
    memory_usage_mb = models.FloatField(null=True, blank=True)
    cpu_percent = models.FloatField(null=True, blank=True)

    # Database metrics
    db_connections = models.PositiveIntegerField(null=True, blank=True)
    db_query_time_ms = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["job", "-timestamp"]),
        ]

    def __str__(self):
        return f"Metrics for {self.job.name} at {self.timestamp}"


class ProcessingResult(models.Model):
    """Aggregated results from processing jobs."""

    job = models.OneToOneField(
        ProcessingJob, on_delete=models.CASCADE, related_name="result"
    )

    # Aggregated data
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    min_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    max_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Categorized results
    results_by_category = models.JSONField(default=dict)

    # Performance stats
    total_processing_time = models.FloatField(default=0)  # seconds
    average_item_time = models.FloatField(default=0)  # seconds

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Results for {self.job.name}"
