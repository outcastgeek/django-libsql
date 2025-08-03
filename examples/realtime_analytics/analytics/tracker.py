"""Real-time event tracking with Turso sync."""

import threading
import time
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any

from django.db import connections, transaction
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q, F

from .models import (
    Website,
    PageView,
    Event,
    Session,
    RealtimeVisitor,
    HourlyStats,
    DailyStats,
)


class RealtimeTracker:
    """Handles real-time event tracking and aggregation."""

    def __init__(self):
        self.event_buffer = defaultdict(list)
        self.buffer_lock = threading.Lock()
        self.flush_interval = 1.0  # Flush every second
        self.aggregation_interval = 60  # Aggregate every minute
        self.is_running = False

    def start(self):
        """Start background threads for processing."""
        if self.is_running:
            return

        self.is_running = True

        # Start flush thread
        flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        flush_thread.start()

        # Start aggregation thread
        agg_thread = threading.Thread(target=self._aggregation_loop, daemon=True)
        agg_thread.start()

        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        cleanup_thread.start()

    def track_pageview(self, data: Dict[str, Any]):
        """Track a page view event."""
        with self.buffer_lock:
            self.event_buffer["pageviews"].append(data)

    def track_event(self, data: Dict[str, Any]):
        """Track a custom event."""
        with self.buffer_lock:
            self.event_buffer["events"].append(data)

    def _flush_loop(self):
        """Continuously flush events to database."""
        while self.is_running:
            time.sleep(self.flush_interval)
            self._flush_events()

    def _flush_events(self):
        """Flush buffered events to database."""
        # Ensure clean connection
        connections.close_all()

        with self.buffer_lock:
            pageviews = self.event_buffer["pageviews"][:]
            events = self.event_buffer["events"][:]
            self.event_buffer["pageviews"] = []
            self.event_buffer["events"] = []

        if not pageviews and not events:
            return

        try:
            with transaction.atomic():
                # Process pageviews
                for pv_data in pageviews:
                    self._process_pageview(pv_data)

                # Process events
                for event_data in events:
                    self._process_event(event_data)

        except Exception as e:
            print(f"Error flushing events: {e}")

    def _process_pageview(self, data: Dict[str, Any]):
        """Process a single pageview."""
        website = Website.objects.get(tracking_id=data["tracking_id"])

        # Create pageview
        pageview = PageView.objects.create(
            website=website,
            session_id=data["session_id"],
            page_path=data["page_path"],
            page_title=data.get("page_title", ""),
            ip_address=data["ip_address"],
            user_agent=data["user_agent"],
            referrer_url=data.get("referrer_url", ""),
            referrer_domain=data.get("referrer_domain", ""),
            device_type=data.get("device_type", "desktop"),
            browser=data.get("browser", "Unknown"),
            os=data.get("os", "Unknown"),
            country=data.get("country", ""),
            city=data.get("city", ""),
            page_load_time=data.get("page_load_time"),
            timestamp=timezone.now(),
        )

        # Update realtime visitors
        RealtimeVisitor.objects.update_or_create(
            website=website,
            session_id=data["session_id"],
            defaults={
                "page_path": data["page_path"],
                "ip_address": data["ip_address"],
                "country": data.get("country", ""),
                "device_type": data.get("device_type", "desktop"),
                "last_seen": timezone.now(),
            },
        )

        # Update or create session
        session, created = Session.objects.get_or_create(
            session_id=data["session_id"],
            defaults={
                "website": website,
                "started_at": timezone.now(),
                "ip_address": data["ip_address"],
                "country": data.get("country", ""),
                "device_type": data.get("device_type", "desktop"),
                "browser": data.get("browser", "Unknown"),
                "entry_page": data["page_path"],
            },
        )

        if not created:
            # Update existing session
            session.pageview_count = F("pageview_count") + 1
            session.ended_at = timezone.now()
            session.exit_page = data["page_path"]
            session.duration_seconds = (
                timezone.now() - session.started_at
            ).total_seconds()
            session.bounce = session.pageview_count == 1
            session.save()

    def _process_event(self, data: Dict[str, Any]):
        """Process a custom event."""
        website = Website.objects.get(tracking_id=data["tracking_id"])

        # Find associated pageview if any
        pageview = None
        if data.get("pageview_id"):
            try:
                pageview = PageView.objects.get(id=data["pageview_id"])
            except PageView.DoesNotExist:
                pass

        # Create event
        Event.objects.create(
            website=website,
            session_id=data["session_id"],
            pageview=pageview,
            event_type=data["event_type"],
            event_name=data["event_name"],
            event_value=data.get("event_value", ""),
            event_data=data.get("event_data", {}),
            timestamp=timezone.now(),
        )

        # Update session event count
        Session.objects.filter(session_id=data["session_id"]).update(
            event_count=F("event_count") + 1
        )

    def _aggregation_loop(self):
        """Continuously aggregate statistics."""
        while self.is_running:
            time.sleep(self.aggregation_interval)
            self._aggregate_stats()

    def _aggregate_stats(self):
        """Aggregate statistics for all websites."""
        # Ensure clean connection
        connections.close_all()

        try:
            for website in Website.objects.filter(is_active=True):
                self._aggregate_website_stats(website)
        except Exception as e:
            print(f"Error aggregating stats: {e}")

    def _aggregate_website_stats(self, website: Website):
        """Aggregate stats for a single website."""
        now = timezone.now()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        hour_ago = now - timedelta(hours=1)

        # Get pageviews for current hour
        hour_pageviews = PageView.objects.filter(
            website=website,
            timestamp__gte=current_hour,
            timestamp__lt=current_hour + timedelta(hours=1),
        )

        # Calculate metrics
        pageview_count = hour_pageviews.count()
        unique_visitors = hour_pageviews.values("session_id").distinct().count()

        # Get sessions for current hour
        hour_sessions = Session.objects.filter(
            website=website,
            started_at__gte=current_hour,
            started_at__lt=current_hour + timedelta(hours=1),
        )

        session_count = hour_sessions.count()
        bounce_count = hour_sessions.filter(bounce=True).count()

        # Get events for current hour
        event_count = Event.objects.filter(
            website=website,
            timestamp__gte=current_hour,
            timestamp__lt=current_hour + timedelta(hours=1),
        ).count()

        # Performance metrics
        avg_load_time = hour_pageviews.aggregate(avg=Avg("page_load_time"))["avg"]

        avg_session_duration = hour_sessions.aggregate(avg=Avg("duration_seconds"))[
            "avg"
        ]

        # Top pages
        top_pages = list(
            hour_pageviews.values("page_path")
            .annotate(views=Count("id"))
            .order_by("-views")[:10]
        )

        # Top referrers
        top_referrers = list(
            hour_pageviews.exclude(referrer_domain="")
            .values("referrer_domain")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Device breakdown
        device_breakdown = dict(
            hour_pageviews.values("device_type")
            .annotate(count=Count("id"))
            .values_list("device_type", "count")
        )

        # Update or create hourly stats
        HourlyStats.objects.update_or_create(
            website=website,
            hour=current_hour,
            defaults={
                "pageviews": pageview_count,
                "unique_visitors": unique_visitors,
                "sessions": session_count,
                "bounces": bounce_count,
                "events": event_count,
                "avg_page_load_time": avg_load_time,
                "avg_session_duration": avg_session_duration,
                "top_pages": top_pages,
                "top_referrers": top_referrers,
                "device_breakdown": device_breakdown,
            },
        )

        # Update daily stats
        self._update_daily_stats(website)

    def _update_daily_stats(self, website: Website):
        """Update daily statistics."""
        today = timezone.now().date()

        # Aggregate from hourly stats
        daily_data = HourlyStats.objects.filter(
            website=website, hour__date=today
        ).aggregate(
            pageviews=Sum("pageviews"),
            unique_visitors=Sum("unique_visitors"),
            sessions=Sum("sessions"),
            bounces=Sum("bounces"),
            events=Sum("events"),
            avg_load_time=Avg("avg_page_load_time"),
            avg_duration=Avg("avg_session_duration"),
        )

        # Calculate additional metrics
        bounce_rate = None
        if daily_data["sessions"] and daily_data["sessions"] > 0:
            bounce_rate = (daily_data["bounces"] / daily_data["sessions"]) * 100

        pages_per_session = None
        if daily_data["sessions"] and daily_data["sessions"] > 0:
            pages_per_session = daily_data["pageviews"] / daily_data["sessions"]

        # Get yesterday's stats for growth calculation
        yesterday = today - timedelta(days=1)
        yesterday_stats = DailyStats.objects.filter(
            website=website, date=yesterday
        ).first()

        pageviews_growth = None
        visitors_growth = None

        if yesterday_stats:
            if yesterday_stats.pageviews > 0:
                pageviews_growth = (
                    (daily_data["pageviews"] - yesterday_stats.pageviews)
                    / yesterday_stats.pageviews
                    * 100
                )
            if yesterday_stats.unique_visitors > 0:
                visitors_growth = (
                    (daily_data["unique_visitors"] - yesterday_stats.unique_visitors)
                    / yesterday_stats.unique_visitors
                    * 100
                )

        # Update or create daily stats
        DailyStats.objects.update_or_create(
            website=website,
            date=today,
            defaults={
                "pageviews": daily_data["pageviews"] or 0,
                "unique_visitors": daily_data["unique_visitors"] or 0,
                "sessions": daily_data["sessions"] or 0,
                "bounces": daily_data["bounces"] or 0,
                "bounce_rate": bounce_rate,
                "events": daily_data["events"] or 0,
                "avg_page_load_time": daily_data["avg_load_time"],
                "avg_session_duration": daily_data["avg_duration"],
                "pages_per_session": pages_per_session,
                "pageviews_growth": pageviews_growth,
                "visitors_growth": visitors_growth,
            },
        )

    def _cleanup_loop(self):
        """Periodically clean up old data."""
        while self.is_running:
            time.sleep(300)  # Run every 5 minutes
            self._cleanup_old_data()

    def _cleanup_old_data(self):
        """Remove old data based on retention settings."""
        # Ensure clean connection
        connections.close_all()

        try:
            # Clean up old realtime visitors
            RealtimeVisitor.cleanup_old()

            # Clean up old pageviews (keep 30 days)
            cutoff = timezone.now() - timedelta(days=30)
            PageView.objects.filter(timestamp__lt=cutoff).delete()
            Event.objects.filter(timestamp__lt=cutoff).delete()

            # Clean up old sessions
            Session.objects.filter(started_at__lt=cutoff).delete()

            # Keep hourly stats for 7 days
            hourly_cutoff = timezone.now() - timedelta(days=7)
            HourlyStats.objects.filter(hour__lt=hourly_cutoff).delete()

        except Exception as e:
            print(f"Error cleaning up old data: {e}")


# Global tracker instance
tracker = RealtimeTracker()
