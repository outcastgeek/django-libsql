"""URL configuration for GIL benchmark app."""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('benchmark_app.urls')),
]