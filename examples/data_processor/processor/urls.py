"""URL patterns for processor app."""

from django.urls import path
from . import views

app_name = "processor"

urlpatterns = [
    path("", views.index, name="index"),
    path("job/<int:job_id>/", views.job_detail, name="job_detail"),
    path("job/<int:job_id>/status/", views.job_status, name="job_status"),
    path("job/<int:job_id>/cancel/", views.cancel_job, name="cancel_job"),
    path("create-job/", views.create_job, name="create_job"),
    path("compare-performance/", views.compare_performance, name="compare_performance"),
]
