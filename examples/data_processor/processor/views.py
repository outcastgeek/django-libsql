"""Views for data processor app demonstrating concurrent processing."""

import threading
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q, Avg, Sum, Max, F
from django.utils import timezone
from django.conf import settings

from .models import DataSource, ProcessingJob, DataItem, ProcessingMetrics
from .processing import process_job_async


def index(request):
    """Dashboard showing processing jobs and metrics."""
    # Recent jobs
    recent_jobs = ProcessingJob.objects.select_related("data_source").order_by(
        "-created_at"
    )[:10]

    # Job statistics
    job_stats = ProcessingJob.objects.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="pending")),
        running=Count("id", filter=Q(status="running")),
        completed=Count("id", filter=Q(status="completed")),
        failed=Count("id", filter=Q(status="failed")),
    )

    # Performance metrics
    recent_metrics = ProcessingMetrics.objects.filter(
        timestamp__gte=timezone.now() - timezone.timedelta(hours=1)
    ).aggregate(
        avg_items_per_second=Avg("items_per_second"),
        max_items_per_second=Max("items_per_second"),
    )

    # Active data sources
    data_sources = DataSource.objects.filter(is_active=True).annotate(
        job_count=Count("jobs")
    )

    context = {
        "recent_jobs": recent_jobs,
        "job_stats": job_stats,
        "recent_metrics": recent_metrics,
        "data_sources": data_sources,
        "gil_status": "DISABLED"
        if settings.DATA_PROCESSOR_SETTINGS["ENABLE_NO_GIL"]
        else "ENABLED",
        "max_workers": settings.DATA_PROCESSOR_SETTINGS["MAX_WORKERS"],
    }

    return render(request, "processor/index.html", context)


def job_detail(request, job_id):
    """Detailed view of a processing job."""
    job = get_object_or_404(
        ProcessingJob.objects.select_related("data_source"), id=job_id
    )

    # Item statistics
    item_stats = DataItem.objects.filter(job=job).aggregate(
        total=Count("id"),
        processed=Count("id", filter=Q(is_processed=True)),
        failed=Count("id", filter=Q(is_failed=True)),
        avg_time=Avg("processing_time", filter=Q(is_processed=True)),
    )

    # Recent metrics
    metrics = ProcessingMetrics.objects.filter(job=job).order_by("-timestamp")[:20]

    # Sample processed items
    sample_items = DataItem.objects.filter(job=job, is_processed=True).order_by(
        "-processed_at"
    )[:10]

    # Failed items
    failed_items = DataItem.objects.filter(job=job, is_failed=True)[:10]

    context = {
        "job": job,
        "item_stats": item_stats,
        "metrics": metrics,
        "sample_items": sample_items,
        "failed_items": failed_items,
    }

    return render(request, "processor/job_detail.html", context)


@require_http_methods(["POST"])
def create_job(request):
    """Create a new processing job."""
    data_source_id = request.POST.get("data_source")
    name = request.POST.get("name")

    if not data_source_id or not name:
        return JsonResponse({"error": "Missing required fields"}, status=400)

    data_source = get_object_or_404(DataSource, id=data_source_id)

    # Create job
    job = ProcessingJob.objects.create(
        name=name,
        data_source=data_source,
        batch_size=int(request.POST.get("batch_size", 100)),
        num_workers=int(request.POST.get("num_workers", 4)),
        config={
            "processing_type": request.POST.get("processing_type", "standard"),
            "options": json.loads(request.POST.get("options", "{}")),
        },
    )

    # Generate sample data items
    num_items = int(request.POST.get("num_items", 1000))
    items = []
    for i in range(num_items):
        items.append(
            DataItem(
                job=job,
                external_id=f"item_{i}",
                data={
                    "id": i,
                    "value": i * 10 + (i % 7),  # Some variation
                    "category": f"cat_{i % 5}",
                    "timestamp": timezone.now().isoformat(),
                },
            )
        )

    # Bulk create items
    DataItem.objects.bulk_create(items, batch_size=500)

    # Start processing in a separate thread
    thread = threading.Thread(target=process_job_async, args=(job.id,))
    thread.daemon = True
    thread.start()

    return JsonResponse(
        {
            "job_id": job.id,
            "status": "started",
            "message": f"Job created with {num_items} items",
        }
    )


@require_http_methods(["GET"])
def job_status(request, job_id):
    """Get current status of a job via AJAX."""
    job = get_object_or_404(ProcessingJob, id=job_id)

    # Get latest metrics
    latest_metric = (
        ProcessingMetrics.objects.filter(job=job).order_by("-timestamp").first()
    )

    response = {
        "id": job.id,
        "status": job.status,
        "progress": job.progress_percentage,
        "processed_items": job.processed_items,
        "failed_items": job.failed_items,
        "total_items": job.total_items,
        "duration": job.duration,
        "items_per_second": job.items_per_second,
    }

    if latest_metric:
        response["current_rate"] = latest_metric.items_per_second
        response["queue_size"] = latest_metric.queue_size

    return JsonResponse(response)


@require_http_methods(["POST"])
def cancel_job(request, job_id):
    """Cancel a running job."""
    job = get_object_or_404(ProcessingJob, id=job_id)

    if job.status in ["pending", "running"]:
        job.status = "cancelled"
        job.completed_at = timezone.now()
        job.save()

        return JsonResponse({"message": "Job cancelled successfully"})

    return JsonResponse({"error": "Job cannot be cancelled"}, status=400)


def compare_performance(request):
    """Compare performance with and without GIL."""
    # Get jobs grouped by worker count
    performance_data = (
        ProcessingJob.objects.filter(status="completed")
        .values("num_workers")
        .annotate(
            avg_items_per_sec=Avg("processed_items") / Avg("duration"),
            job_count=Count("id"),
        )
        .order_by("num_workers")
    )

    context = {
        "performance_data": list(performance_data),
        "gil_status": "DISABLED"
        if settings.DATA_PROCESSOR_SETTINGS["ENABLE_NO_GIL"]
        else "ENABLED",
    }

    return render(request, "processor/compare_performance.html", context)
