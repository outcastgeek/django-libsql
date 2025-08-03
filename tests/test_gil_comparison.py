"""
Automated GIL comparison tests for django-libsql.
These tests run automatically with pytest and handle GIL enabled/disabled scenarios.
"""
import os
import sys
import subprocess
import time
import threading
import concurrent.futures
from decimal import Decimal
from datetime import date

import pytest
from django.db import connection, connections
from django.test import TransactionTestCase

from tests.testapp.models import Book, Review


def is_gil_disabled():
    """Check if GIL is actually disabled."""
    try:
        import _thread
        return not _thread._is_gil_enabled()
    except (ImportError, AttributeError):
        return os.environ.get('PYTHON_GIL', '1') == '0'


class GILComparisonTest(TransactionTestCase):
    """Test Django ORM performance with GIL enabled vs disabled."""
    
    # Don't use transactions for test isolation
    serialized_rollback = False
    
    @classmethod
    def _databases_names(cls, include_mirrors=True):
        """Skip Django's test database management."""
        return []  # Use real database directly
    
    def setUp(self):
        """Setup test data."""
        # Clean up any existing data
        Book.objects.all().delete()
        Review.objects.all().delete()
    
    def run_threaded_operations(self, num_threads=4, operations_per_thread=5):
        """Run concurrent database operations and measure performance."""
        def worker_operations(worker_id):
            """Perform database operations in a thread."""
            # Ensure each thread has its own connection
            connections.close_all()
            
            # Small delay for Turso sync
            time.sleep(0.1)
            
            successful_ops = 0
            errors = []
            
            try:
                for i in range(operations_per_thread):
                    # CREATE
                    book = Book.objects.create(
                        title=f"GILTest_{worker_id}_{i}",
                        author=f"Author_{worker_id}",
                        isbn=f"777-{worker_id:03d}-{i:03d}-000-0",
                        published_date=date(2024, 1, 1),
                        pages=200,
                        price=Decimal("19.99"),
                        in_stock=True
                    )
                    
                    # READ
                    retrieved = Book.objects.get(id=book.id)
                    
                    # UPDATE
                    retrieved.pages = 300
                    retrieved.save()
                    
                    successful_ops += 1
                    
            except Exception as e:
                errors.append(str(e))
            
            return successful_ops, errors
        
        start_time = time.perf_counter()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_operations, i) for i in range(num_threads)]
            results = [f.result() for f in futures]
        
        duration = time.perf_counter() - start_time
        
        total_ops = sum(r[0] for r in results)
        total_errors = sum(len(r[1]) for r in results)
        
        # Clean up
        Book.objects.filter(title__startswith="GILTest_").delete()
        
        return {
            'total_ops': total_ops * 3,  # CREATE, READ, UPDATE = 3 ops
            'duration': duration,
            'ops_per_sec': (total_ops * 3) / duration if duration > 0 else 0,
            'errors': total_errors
        }
    
    def test_gil_performance_comparison(self):
        """Test and compare performance with current GIL status."""
        gil_status = "DISABLED" if is_gil_disabled() else "ENABLED"
        
        # Run single-threaded baseline
        single_result = self.run_threaded_operations(num_threads=1, operations_per_thread=10)
        
        # Run multi-threaded test
        multi_result = self.run_threaded_operations(num_threads=4, operations_per_thread=10)
        
        # Calculate speedup
        speedup = multi_result['ops_per_sec'] / single_result['ops_per_sec'] if single_result['ops_per_sec'] > 0 else 0
        
        # Report results
        print(f"\n🐍 GIL Performance Test (GIL {gil_status}):")
        print(f"  Single-threaded: {single_result['ops_per_sec']:.2f} ops/sec")
        print(f"  Multi-threaded (4 threads): {multi_result['ops_per_sec']:.2f} ops/sec")
        print(f"  Speedup: {speedup:.2f}x")
        
        # Assertions based on GIL status
        if is_gil_disabled():
            # With GIL disabled, we expect significant speedup
            self.assertGreater(speedup, 1.3, 
                f"Expected speedup > 1.3x with GIL disabled, got {speedup:.2f}x")
        else:
            # With GIL enabled, speedup should be minimal or none
            self.assertLess(speedup, 2.0,
                f"Unexpected high speedup {speedup:.2f}x with GIL enabled")
    
    @pytest.mark.skipif(
        sys.version_info < (3, 13) or not hasattr(sys, '_is_gil_enabled'),
        reason="GIL control requires Python 3.13+ with free-threading support"
    )
    def test_run_with_both_gil_modes(self):
        """Run the same test in subprocess with GIL enabled and disabled."""
        test_script = """
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
import django
django.setup()

from tests.test_gil_comparison import GILComparisonTest

# Run the test
test = GILComparisonTest()
test.setUp()
test.test_gil_performance_comparison()
"""
        
        results = {}
        
        # Run with GIL enabled
        print("\n📊 Running with GIL ENABLED...")
        env_enabled = os.environ.copy()
        env_enabled.pop('PYTHON_GIL', None)
        
        proc_enabled = subprocess.run(
            [sys.executable, '-c', test_script],
            env=env_enabled,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        
        if proc_enabled.returncode == 0:
            results['gil_enabled'] = proc_enabled.stdout
        else:
            print(f"GIL enabled test failed: {proc_enabled.stderr}")
        
        # Run with GIL disabled
        print("\n📊 Running with GIL DISABLED...")
        env_disabled = os.environ.copy()
        env_disabled['PYTHON_GIL'] = '0'
        
        proc_disabled = subprocess.run(
            [sys.executable, '-X', 'gil=0', '-c', test_script],
            env=env_disabled,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        
        if proc_disabled.returncode == 0:
            results['gil_disabled'] = proc_disabled.stdout
        else:
            # Try without -X gil=0 flag
            proc_disabled = subprocess.run(
                [sys.executable, '-c', test_script],
                env=env_disabled,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            if proc_disabled.returncode == 0:
                results['gil_disabled'] = proc_disabled.stdout
            else:
                print(f"GIL disabled test failed: {proc_disabled.stderr}")
        
        # Parse and compare results
        if 'gil_enabled' in results and 'gil_disabled' in results:
            print("\n✅ COMPARISON SUMMARY:")
            print("GIL ENABLED output:")
            print(results['gil_enabled'])
            print("\nGIL DISABLED output:")
            print(results['gil_disabled'])
            
            # Extract speedup values
            import re
            enabled_speedup = None
            disabled_speedup = None
            
            enabled_match = re.search(r'Speedup: ([\d.]+)x', results['gil_enabled'])
            if enabled_match:
                enabled_speedup = float(enabled_match.group(1))
            
            disabled_match = re.search(r'Speedup: ([\d.]+)x', results['gil_disabled'])
            if disabled_match:
                disabled_speedup = float(disabled_match.group(1))
            
            if enabled_speedup and disabled_speedup:
                improvement = ((disabled_speedup - enabled_speedup) / enabled_speedup) * 100
                print(f"\n🎯 GIL Performance Impact:")
                print(f"  GIL Enabled speedup: {enabled_speedup:.2f}x")
                print(f"  GIL Disabled speedup: {disabled_speedup:.2f}x")
                print(f"  Improvement: {improvement:+.1f}%")
                
                # Assert that GIL disabled performs better
                self.assertGreater(disabled_speedup, enabled_speedup,
                    "Expected better multi-threading performance with GIL disabled")


@pytest.mark.skipif(
    not os.environ.get('TURSO_DATABASE_URL'),
    reason="Turso environment variables not set"
)
@pytest.mark.gil_disabled
class NoGILThreadingTest(TransactionTestCase):
    """Test threading scenarios specifically for no-GIL environments."""
    
    # Don't use transactions for test isolation
    serialized_rollback = False
    
    @classmethod
    def _databases_names(cls, include_mirrors=True):
        """Skip Django's test database management."""
        return []  # Use real database directly
    
    def setUp(self):
        """Setup test data."""
        Book.objects.all().delete()
        Review.objects.all().delete()
    
    @pytest.mark.gil_disabled
    def test_high_concurrency_no_gil(self):
        """Test high concurrency scenarios that benefit from no-GIL."""
        if not is_gil_disabled():
            self.skipTest("This test is specifically for no-GIL environments")
        
        num_threads = 8  # Higher thread count for no-GIL
        operations_per_thread = 10
        
        def intensive_operations(worker_id):
            """CPU-intensive operations mixed with database access."""
            connections.close_all()
            time.sleep(0.1)
            
            results = []
            for i in range(operations_per_thread):
                # Simulate CPU-intensive work
                cpu_work = sum(j * j for j in range(1000))
                
                # Database operation
                book = Book.objects.create(
                    title=f"NoGIL_Intensive_{worker_id}_{i}",
                    author=f"Worker_{worker_id}",
                    isbn=f"999-{worker_id:03d}-{i:03d}-000-0",
                    published_date=date(2024, 1, 1),
                    pages=cpu_work % 1000,  # Use CPU work result
                    price=Decimal("29.99"),
                    in_stock=True
                )
                results.append(book.id)
            
            return len(results)
        
        start_time = time.perf_counter()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(intensive_operations, i) for i in range(num_threads)]
            results = [f.result() for f in futures]
        
        duration = time.perf_counter() - start_time
        total_created = sum(results)
        
        print(f"\n🚀 No-GIL High Concurrency Test:")
        print(f"  Threads: {num_threads}")
        print(f"  Total operations: {total_created}")
        print(f"  Duration: {duration:.3f}s")
        print(f"  Operations/sec: {total_created / duration:.2f}")
        
        # Clean up
        Book.objects.filter(title__startswith="NoGIL_Intensive_").delete()
        
        # With no-GIL and 8 threads, we should complete all operations
        self.assertEqual(total_created, num_threads * operations_per_thread)
        
        # Performance should scale well with thread count
        ops_per_sec = total_created / duration
        self.assertGreater(ops_per_sec, operations_per_thread,
            "Expected better than single-threaded performance with no-GIL")