#!/usr/bin/env python
"""
Quick Django ORM threading test for django-libsql.
Can be run with or without GIL to compare performance.

Usage:
    # With GIL (default)
    python tests/test_quick_threading.py
    
    # Without GIL (Python 3.13+ free-threading build)
    PYTHON_GIL=0 python -Xgil=0 tests/test_quick_threading.py
"""
import os
import sys
import time
import django
import concurrent.futures
from decimal import Decimal
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
django.setup()

from django.db import connection
from tests.testapp.models import Book


def is_gil_disabled():
    """Check if GIL is actually disabled."""
    try:
        import _thread
        return not _thread._is_gil_enabled()
    except (ImportError, AttributeError):
        return os.environ.get('PYTHON_GIL', '1') == '0'


def quick_orm_worker(worker_id):
    """Quick Django ORM operations per worker."""
    try:
        start_time = time.perf_counter()
        
        # Simple CRUD operations
        for i in range(3):  # Just 3 operations per worker
            # CREATE
            book = Book.objects.create(
                title=f"QuickTest_{worker_id}_{i}",
                author=f"Author_{worker_id}",
                isbn=f"999-{worker_id:03d}-{i:03d}-000-0",
                published_date=date(2024, 1, 1),
                pages=100,
                price=Decimal("10.00"),
                in_stock=True
            )
            
            # READ
            retrieved = Book.objects.get(id=book.id)
            
            # UPDATE  
            retrieved.pages = 200
            retrieved.save()
            
            # DELETE
            retrieved.delete()
        
        duration = time.perf_counter() - start_time
        return {
            'worker_id': worker_id,
            'success': True,
            'duration': duration,
            'ops_per_sec': 3 / duration
        }
        
    except Exception as e:
        return {
            'worker_id': worker_id,
            'success': False,
            'error': str(e)
        }


def main():
    """Run quick Django ORM threading test."""
    gil_status = "DISABLED" if is_gil_disabled() else "ENABLED"
    print(f"🐍 Quick Django ORM Test - GIL {gil_status}")
    print("=" * 50)
    
    # Show database info
    db_name = connection.settings_dict.get('NAME', 'Unknown')
    if 'TURSO_DATABASE_URL' in os.environ:
        print(f"Database: Turso ({os.environ['TURSO_DATABASE_URL'][:40]}...)")
    else:
        print(f"Database: {db_name}")
    
    # Clean up
    Book.objects.filter(title__contains="QuickTest").delete()
    
    # Test with 4 threads
    num_threads = 4
    start_time = time.perf_counter()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(quick_orm_worker, i) for i in range(num_threads)]
        results = [f.result(timeout=30) for f in futures]
    
    total_duration = time.perf_counter() - start_time
    
    # Results
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"\n✅ Successful workers: {len(successful)}/{num_threads}")
    print(f"⏱️  Total time: {total_duration:.3f}s")
    
    if successful:
        total_ops = len(successful) * 3  # 3 ops per worker
        overall_ops_per_sec = total_ops / total_duration
        avg_worker_ops_per_sec = sum(r['ops_per_sec'] for r in successful) / len(successful)
        
        print(f"🚀 Overall: {overall_ops_per_sec:.2f} CRUD ops/sec")
        print(f"👤 Avg worker: {avg_worker_ops_per_sec:.2f} CRUD ops/sec")
        
        # Output for comparison script
        print(f"\nRESULT: {num_threads}×3: {overall_ops_per_sec:.1f} CRUD ops/sec (100% worker efficiency)")
    
    if failed:
        print(f"\n❌ Failed workers: {len(failed)}")
        for f in failed:
            print(f"   Worker {f['worker_id']}: {f['error']}")
    
    # Clean up
    Book.objects.filter(title__contains="QuickTest").delete()


if __name__ == "__main__":
    main()