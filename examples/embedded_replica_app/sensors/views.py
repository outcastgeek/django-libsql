import json
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Avg, Min, Max, Count, Q
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.db import connection

from .models import SensorReading, AggregatedData, SyncLog


def index(request):
    """Main dashboard view."""
    # Get recent readings
    recent_readings = SensorReading.objects.order_by('-timestamp')[:10]
    
    # Get sensor stats
    sensor_stats = SensorReading.objects.values('sensor_id').annotate(
        avg_temp=Avg('temperature'),
        avg_humidity=Avg('humidity'),
        reading_count=Count('id')
    ).order_by('-reading_count')[:5]
    
    # Get sync status
    latest_sync = SyncLog.objects.order_by('-sync_time').first()
    
    # Check if running embedded replica
    is_embedded = hasattr(connection, 'sync')
    
    context = {
        'recent_readings': recent_readings,
        'sensor_stats': sensor_stats,
        'latest_sync': latest_sync,
        'is_embedded': is_embedded,
        'gil_status': get_gil_status(),
    }
    
    return render(request, 'sensors/dashboard.html', context)


def api_readings(request):
    """API endpoint for sensor readings."""
    # Get query parameters
    hours = int(request.GET.get('hours', 1))
    sensor_id = request.GET.get('sensor_id')
    
    # Build query
    cutoff = timezone.now() - timedelta(hours=hours)
    readings = SensorReading.objects.filter(timestamp__gte=cutoff)
    
    if sensor_id:
        readings = readings.filter(sensor_id=sensor_id)
    
    # Get data
    data = list(readings.values('sensor_id', 'temperature', 'humidity', 'pressure', 'timestamp').order_by('-timestamp')[:100])
    
    # Convert timestamps to strings
    for item in data:
        item['timestamp'] = item['timestamp'].isoformat()
    
    return JsonResponse({
        'readings': data,
        'count': len(data),
        'is_embedded': hasattr(connection, 'sync'),
    })


def api_stats(request):
    """API endpoint for aggregated statistics."""
    # Get time range
    hours = int(request.GET.get('hours', 24))
    cutoff = timezone.now() - timedelta(hours=hours)
    
    # Get aggregated data
    stats = AggregatedData.objects.filter(
        hour__gte=cutoff
    ).values('sensor_id').annotate(
        avg_temp=Avg('avg_temperature'),
        min_temp=Min('min_temperature'),
        max_temp=Max('max_temperature'),
        total_readings=Count('id')
    )
    
    return JsonResponse({
        'stats': list(stats),
        'time_range_hours': hours,
    })


@csrf_exempt
def api_sync(request):
    """Manually trigger sync for embedded replicas."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    if not hasattr(connection, 'sync'):
        return JsonResponse({
            'error': 'Not using embedded replica',
            'message': 'Manual sync only available for embedded replicas'
        }, status=400)
    
    try:
        # Perform sync
        connection.sync()
        
        # Log it
        SyncLog.objects.create(
            sync_type='manual',
            records_synced=0,  # We don't know exact count
            success=True,
            details={'triggered_by': 'api'}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Sync completed successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_gil_status():
    """Check if Python is running with GIL disabled."""
    import sys
    gil_disabled = sys._is_gil_enabled() == False if hasattr(sys, '_is_gil_enabled') else False
    return "NO-GIL" if gil_disabled else "WITH-GIL"