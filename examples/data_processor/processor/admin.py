"""Admin configuration for processor app."""

from django.contrib import admin
from .models import (
    DataSource,
    ProcessingJob,
    DataItem,
    ProcessingMetrics,
    ProcessingResult,
)


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "last_fetched", "job_count", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "url"]

    def job_count(self, obj):
        return obj.jobs.count()

    job_count.short_description = "Jobs"


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "data_source",
        "status",
        "progress_percentage",
        "processed_items",
        "failed_items",
        "created_at",
    ]
    list_filter = ["status", "data_source", "created_at"]
    search_fields = ["name"]
    readonly_fields = [
        "started_at",
        "completed_at",
        "total_items",
        "processed_items",
        "failed_items",
        "result_summary",
    ]

    fieldsets = (
        (None, {"fields": ("name", "data_source", "status")}),
        ("Configuration", {"fields": ("config", "batch_size", "num_workers")}),
        (
            "Progress",
            {
                "fields": (
                    "total_items",
                    "processed_items",
                    "failed_items",
                    "started_at",
                    "completed_at",
                )
            },
        ),
        (
            "Results",
            {"fields": ("result_summary", "error_log"), "classes": ("collapse",)},
        ),
    )


@admin.register(DataItem)
class DataItemAdmin(admin.ModelAdmin):
    list_display = [
        "external_id",
        "job",
        "is_processed",
        "is_failed",
        "processing_time",
        "created_at",
    ]
    list_filter = ["is_processed", "is_failed", "job"]
    search_fields = ["external_id", "error_message"]
    readonly_fields = ["processed_at", "processing_time"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("job")


@admin.register(ProcessingMetrics)
class ProcessingMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "job",
        "timestamp",
        "items_per_second",
        "active_workers",
        "queue_size",
    ]
    list_filter = ["job", "timestamp"]
    date_hierarchy = "timestamp"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("job")


@admin.register(ProcessingResult)
class ProcessingResultAdmin(admin.ModelAdmin):
    list_display = [
        "job",
        "total_value",
        "average_value",
        "total_processing_time",
        "created_at",
    ]
    readonly_fields = [
        "total_value",
        "average_value",
        "min_value",
        "max_value",
        "results_by_category",
        "total_processing_time",
        "average_item_time",
    ]
