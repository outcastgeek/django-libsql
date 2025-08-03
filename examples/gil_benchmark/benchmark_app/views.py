import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.db import connection
import sys
import io

from .models import BenchmarkResult


def index(request):
    """Main benchmark dashboard."""
    # Get recent results
    recent_results = BenchmarkResult.objects.order_by('-timestamp')[:20]
    
    # Get best results by test type
    best_results = {}
    for test in ['crud', 'read', 'write', 'mixed']:
        best = BenchmarkResult.objects.filter(
            test_name=test
        ).order_by('-throughput').first()
        if best:
            best_results[test] = best
    
    # Check environment
    gil_status = "NO-GIL" if hasattr(sys, '_is_gil_enabled') and not sys._is_gil_enabled() else "WITH-GIL"
    is_embedded = hasattr(connection, 'sync')
    
    context = {
        'recent_results': recent_results,
        'best_results': best_results,
        'gil_status': gil_status,
        'is_embedded': is_embedded,
    }
    
    return render(request, 'benchmark_app/dashboard.html', context)


def results(request):
    """API endpoint for benchmark results."""
    # Get filters
    test_name = request.GET.get('test')
    mode = request.GET.get('mode')
    limit = int(request.GET.get('limit', 50))
    
    # Build query
    results = BenchmarkResult.objects.all()
    
    if test_name:
        results = results.filter(test_name=test_name)
    if mode:
        results = results.filter(mode__icontains=mode)
    
    # Get data
    data = list(results.order_by('-timestamp')[:limit].values())
    
    # Convert timestamps
    for item in data:
        item['timestamp'] = item['timestamp'].isoformat()
    
    return JsonResponse({
        'results': data,
        'count': len(data),
    })


@csrf_exempt
def run_benchmark(request):
    """Run benchmark via API."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    # Get parameters
    body = json.loads(request.body) if request.body else {}
    test_type = body.get('test', 'crud')
    operations = body.get('operations', 100)
    threads = body.get('threads', 1)
    
    # Capture output
    output = io.StringIO()
    
    try:
        # Run benchmark command
        call_command(
            'run_benchmark',
            test=test_type,
            operations=operations,
            threads=threads,
            stdout=output
        )
        
        # Get output
        result_text = output.getvalue()
        
        # Get latest result
        latest = BenchmarkResult.objects.order_by('-timestamp').first()
        
        return JsonResponse({
            'success': True,
            'output': result_text,
            'result': {
                'test_name': latest.test_name,
                'throughput': latest.throughput,
                'duration': latest.duration,
                'mode': latest.mode,
            } if latest else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)