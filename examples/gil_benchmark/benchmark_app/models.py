from django.db import models


class BenchmarkResult(models.Model):
    """Store benchmark results for analysis."""
    test_name = models.CharField(max_length=100)
    mode = models.CharField(max_length=50)  # gil, no-gil, embedded, remote
    threads = models.IntegerField(default=1)
    operations = models.IntegerField()
    duration = models.FloatField()  # seconds
    throughput = models.FloatField()  # ops/sec
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional metadata
    python_version = models.CharField(max_length=50)
    gil_enabled = models.BooleanField(default=True)
    is_embedded = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['test_name', 'mode']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.test_name} - {self.mode} - {self.throughput:.2f} ops/sec"


class TestRecord(models.Model):
    """Test records for CRUD operations."""
    name = models.CharField(max_length=100, db_index=True)
    value = models.IntegerField()
    data = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['name', 'value']),
            models.Index(fields=['created_at']),
        ]