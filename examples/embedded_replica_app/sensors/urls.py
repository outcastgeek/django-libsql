from django.urls import path
from . import views

app_name = 'sensors'

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('api/readings/', views.api_readings, name='api_readings'),
    path('api/stats/', views.api_stats, name='api_stats'),
    path('api/sync/', views.api_sync, name='api_sync'),
]