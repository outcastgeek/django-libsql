from django.contrib import admin
from .models import SensorReading, AggregatedData, SyncLog


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ['sensor_id', 'location', 'temperature', 'humidity', 'timestamp', 'synced']
    list_filter = ['location', 'timestamp', 'synced']
    search_fields = ['sensor_id']
    date_hierarchy = 'timestamp'


@admin.register(AggregatedData)
class AggregatedDataAdmin(admin.ModelAdmin):
    list_display = ['sensor_id', 'date', 'avg_temperature', 'avg_humidity', 'reading_count']
    list_filter = ['date']
    search_fields = ['sensor_id']
    date_hierarchy = 'date'


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'sync_type', 'records_synced', 'success', 'duration_ms']
    list_filter = ['sync_type', 'success']
    date_hierarchy = 'timestamp'