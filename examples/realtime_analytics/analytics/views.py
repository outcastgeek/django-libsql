"""Views for real-time analytics dashboard."""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import (
    Website,
    PageView,
    Event,
    Session,
    RealtimeVisitor,
    HourlyStats,
    DailyStats,
)
from .tracker import tracker


def dashboard(request, tracking_id=None):
    """Main analytics dashboard."""
    if tracking_id:
        website = get_object_or_404(Website, tracking_id=tracking_id)
    else:
        website = Website.objects.first()
        if not website:
            return render(request, "analytics/no_data.html")

    # Get current stats
    now = timezone.now()
    today = now.date()

    # Real-time visitors (last 5 minutes)
    realtime_count = RealtimeVisitor.objects.filter(
        website=website, last_seen__gte=now - timedelta(minutes=5)
    ).count()

    # Today's stats
    today_stats = DailyStats.objects.filter(website=website, date=today).first()

    # Last 7 days
    week_ago = today - timedelta(days=7)
    weekly_stats = DailyStats.objects.filter(
        website=website, date__gte=week_ago, date__lte=today
    ).order_by("date")

    # Current hour stats
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    hour_stats = HourlyStats.objects.filter(website=website, hour=current_hour).first()

    # Top pages today
    top_pages = []
    if hour_stats and hour_stats.top_pages:
        top_pages = hour_stats.top_pages[:5]

    # Top referrers today
    top_referrers = []
    if hour_stats and hour_stats.top_referrers:
        top_referrers = hour_stats.top_referrers[:5]

    context = {
        "website": website,
        "websites": Website.objects.filter(is_active=True),
        "realtime_count": realtime_count,
        "today_stats": today_stats or {},
        "weekly_stats": list(weekly_stats),
        "hour_stats": hour_stats or {},
        "top_pages": top_pages,
        "top_referrers": top_referrers,
    }

    return render(request, "analytics/dashboard.html", context)


@require_http_methods(["GET"])
def realtime_data(request, tracking_id):
    """Get real-time data via AJAX."""
    website = get_object_or_404(Website, tracking_id=tracking_id)
    now = timezone.now()

    # Real-time visitors
    visitors = RealtimeVisitor.objects.filter(
        website=website, last_seen__gte=now - timedelta(minutes=5)
    )

    visitor_count = visitors.count()

    # Current visitors by page
    by_page = list(
        visitors.values("page_path")
        .annotate(count=Count("session_id"))
        .order_by("-count")[:10]
    )

    # Recent pageviews (last minute)
    recent_pageviews = PageView.objects.filter(
        website=website, timestamp__gte=now - timedelta(minutes=1)
    ).count()

    # Recent events (last minute)
    recent_events = (
        Event.objects.filter(website=website, timestamp__gte=now - timedelta(minutes=1))
        .values("event_name")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    return JsonResponse(
        {
            "visitor_count": visitor_count,
            "pageviews_per_minute": recent_pageviews,
            "by_page": by_page,
            "recent_events": list(recent_events),
            "timestamp": now.isoformat(),
        }
    )


@require_http_methods(["GET"])
def hourly_data(request, tracking_id):
    """Get hourly data for charts."""
    website = get_object_or_404(Website, tracking_id=tracking_id)
    hours = int(request.GET.get("hours", 24))

    # Get hourly stats
    end_time = timezone.now().replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(hours=hours)

    hourly_stats = HourlyStats.objects.filter(
        website=website, hour__gte=start_time, hour__lte=end_time
    ).order_by("hour")

    # Format for charts
    labels = []
    pageviews = []
    visitors = []
    events = []

    for stat in hourly_stats:
        labels.append(stat.hour.strftime("%H:%M"))
        pageviews.append(stat.pageviews)
        visitors.append(stat.unique_visitors)
        events.append(stat.events)

    return JsonResponse(
        {
            "labels": labels,
            "pageviews": pageviews,
            "visitors": visitors,
            "events": events,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def track_pageview(request):
    """Track a pageview event."""
    try:
        data = json.loads(request.body)

        # Extract user info
        data["ip_address"] = request.META.get("REMOTE_ADDR", "0.0.0.0")
        data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")

        # Track asynchronously
        tracker.track_pageview(data)

        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def track_event(request):
    """Track a custom event."""
    try:
        data = json.loads(request.body)

        # Track asynchronously
        tracker.track_event(data)

        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def compare_periods(request, tracking_id):
    """Compare analytics between two time periods."""
    website = get_object_or_404(Website, tracking_id=tracking_id)

    # Get date ranges
    period = request.GET.get("period", "week")  # week, month, year

    today = timezone.now().date()
    if period == "week":
        current_start = today - timedelta(days=7)
        previous_start = current_start - timedelta(days=7)
        previous_end = current_start - timedelta(days=1)
    elif period == "month":
        current_start = today - timedelta(days=30)
        previous_start = current_start - timedelta(days=30)
        previous_end = current_start - timedelta(days=1)
    else:  # year
        current_start = today - timedelta(days=365)
        previous_start = current_start - timedelta(days=365)
        previous_end = current_start - timedelta(days=1)

    # Get stats for both periods
    current_stats = DailyStats.objects.filter(
        website=website, date__gte=current_start, date__lte=today
    ).aggregate(
        pageviews=Sum("pageviews"),
        visitors=Sum("unique_visitors"),
        sessions=Sum("sessions"),
        bounce_rate=Avg("bounce_rate"),
        events=Sum("events"),
    )

    previous_stats = DailyStats.objects.filter(
        website=website, date__gte=previous_start, date__lte=previous_end
    ).aggregate(
        pageviews=Sum("pageviews"),
        visitors=Sum("unique_visitors"),
        sessions=Sum("sessions"),
        bounce_rate=Avg("bounce_rate"),
        events=Sum("events"),
    )

    # Calculate changes
    changes = {}
    for metric in ["pageviews", "visitors", "sessions", "events"]:
        current = current_stats.get(metric, 0) or 0
        previous = previous_stats.get(metric, 0) or 0

        if previous > 0:
            change = ((current - previous) / previous) * 100
        else:
            change = 100 if current > 0 else 0

        changes[metric] = {
            "current": current,
            "previous": previous,
            "change": round(change, 1),
        }

    # Bounce rate is inverse (lower is better)
    current_bounce = current_stats.get("bounce_rate", 0) or 0
    previous_bounce = previous_stats.get("bounce_rate", 0) or 0

    if previous_bounce > 0:
        bounce_change = ((current_bounce - previous_bounce) / previous_bounce) * 100
    else:
        bounce_change = 0

    changes["bounce_rate"] = {
        "current": round(current_bounce, 1),
        "previous": round(previous_bounce, 1),
        "change": round(bounce_change, 1),
    }

    context = {
        "website": website,
        "period": period,
        "changes": changes,
        "current_start": current_start,
        "previous_start": previous_start,
        "previous_end": previous_end,
    }

    return render(request, "analytics/compare.html", context)
