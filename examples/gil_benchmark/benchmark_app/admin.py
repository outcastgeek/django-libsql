from django.contrib import admin
from .models import BenchmarkResult, TestRecord


@admin.register(BenchmarkResult)
class BenchmarkResultAdmin(admin.ModelAdmin):
    list_display = ['test_name', 'mode', 'threads', 'throughput', 'duration', 'timestamp']
    list_filter = ['test_name', 'gil_enabled', 'is_embedded', 'timestamp']
    search_fields = ['test_name', 'mode']
    date_hierarchy = 'timestamp'
    
    def get_readonly_fields(self, request, obj=None):
        # Make all fields read-only since these are benchmark results
        if obj:
            return [f.name for f in self.model._meta.fields]
        return []


@admin.register(TestRecord)
class TestRecordAdmin(admin.ModelAdmin):
    list_display = ['name', 'value', 'created_at', 'updated_at']
    search_fields = ['name']
    list_filter = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'