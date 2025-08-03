"""Admin configuration for analytics app."""

from django.contrib import admin
from .models import (
    Website,
    PageView,
    Event,
    Session,
    RealtimeVisitor,
    HourlyStats,
    DailyStats,
)


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ["name", "domain", "tracking_id", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "domain", "tracking_id"]


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ["page_path", "website", "session_id", "device_type", "timestamp"]
    list_filter = ["website", "device_type", "timestamp"]
    search_fields = ["page_path", "session_id", "ip_address"]
    date_hierarchy = "timestamp"
    readonly_fields = ["timestamp", "created_at"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["event_name", "event_type", "website", "session_id", "timestamp"]
    list_filter = ["website", "event_type", "timestamp"]
    search_fields = ["event_name", "session_id"]
    date_hierarchy = "timestamp"
    readonly_fields = ["timestamp", "created_at"]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = [
        "session_id",
        "website",
        "pageview_count",
        "event_count",
        "bounce",
        "duration_seconds",
        "started_at",
    ]
    list_filter = ["website", "bounce", "device_type", "started_at"]
    search_fields = ["session_id", "ip_address"]
    date_hierarchy = "started_at"
    readonly_fields = ["started_at", "ended_at", "created_at", "updated_at"]


@admin.register(RealtimeVisitor)
class RealtimeVisitorAdmin(admin.ModelAdmin):
    list_display = ["session_id", "website", "page_path", "device_type", "last_seen"]
    list_filter = ["website", "device_type", "last_seen"]
    search_fields = ["session_id", "page_path", "ip_address"]


@admin.register(HourlyStats)
class HourlyStatsAdmin(admin.ModelAdmin):
    list_display = [
        "website",
        "hour",
        "pageviews",
        "unique_visitors",
        "sessions",
        "events",
        "updated_at",
    ]
    list_filter = ["website", "hour"]
    date_hierarchy = "hour"
    readonly_fields = [
        "top_pages",
        "top_referrers",
        "device_breakdown",
        "created_at",
        "updated_at",
    ]


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = [
        "website",
        "date",
        "pageviews",
        "unique_visitors",
        "bounce_rate",
        "pageviews_growth",
        "updated_at",
    ]
    list_filter = ["website", "date"]
    date_hierarchy = "date"
    readonly_fields = ["created_at", "updated_at"]
