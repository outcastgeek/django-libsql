"""URL patterns for analytics app."""

from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("site/<str:tracking_id>/", views.dashboard, name="site_dashboard"),
    path("site/<str:tracking_id>/realtime/", views.realtime_data, name="realtime_data"),
    path("site/<str:tracking_id>/hourly/", views.hourly_data, name="hourly_data"),
    path("site/<str:tracking_id>/compare/", views.compare_periods, name="compare"),
    # Tracking endpoints
    path("track/pageview/", views.track_pageview, name="track_pageview"),
    path("track/event/", views.track_event, name="track_event"),
]
