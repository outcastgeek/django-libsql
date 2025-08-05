"""
Models for embedded replica demo.
"""

from django.db import models
from django.utils import timezone


class SensorReading(models.Model):
    """Represents IoT sensor readings - perfect for embedded replica pattern."""
    
    sensor_id = models.CharField(max_length=50, db_index=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    humidity = models.DecimalField(max_digits=5, decimal_places=2)
    pressure = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=100)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    synced = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sensor_id', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.sensor_id} @ {self.timestamp}: {self.temperature}°C"


class AggregatedData(models.Model):
    """Aggregated sensor data for analytics."""
    
    sensor_id = models.CharField(max_length=50, db_index=True)
    date = models.DateField(db_index=True)
    avg_temperature = models.DecimalField(max_digits=5, decimal_places=2)
    avg_humidity = models.DecimalField(max_digits=5, decimal_places=2)
    min_temperature = models.DecimalField(max_digits=5, decimal_places=2)
    max_temperature = models.DecimalField(max_digits=5, decimal_places=2)
    reading_count = models.IntegerField()
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['sensor_id', 'date']
        ordering = ['-date', 'sensor_id']
    
    def __str__(self):
        return f"{self.sensor_id} on {self.date}: avg {self.avg_temperature}°C"


class SyncLog(models.Model):
    """Track sync operations for monitoring."""
    
    sync_type = models.CharField(max_length=20, choices=[
        ('manual', 'Manual'),
        ('background', 'Background'),
        ('write', 'After Write'),
    ])
    timestamp = models.DateTimeField(auto_now_add=True)
    duration_ms = models.IntegerField(null=True)
    records_synced = models.IntegerField(null=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.sync_type} sync at {self.timestamp}"