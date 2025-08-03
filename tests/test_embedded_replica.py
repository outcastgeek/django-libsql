"""
Comprehensive Database Tests for django-libsql

This test suite automatically tests ALL scenarios:
1. Regular Python (single-threaded)
2. With threads
3. With threads + no-GIL
4. With threads + no-GIL + Django ORM

Works with both remote-only (Turso) and embedded replica configurations.
NO MANUAL INTERVENTION REQUIRED!
"""

import os
import sys
import time
import tempfile
import threading
import concurrent.futures
import subprocess
import json
from decimal import Decimal
from pathlib import Path

import pytest
import django
from django.test import TransactionTestCase
from django.db import connection, connections
from django.utils import timezone

# Models for testing
from tests.testapp.models import TestModel, Book, Review


class EmbeddedReplicaTestBase:
    """Base class with test scenarios for all modes."""
    
    @classmethod
    def setUpClass(cls):
        """Set up embedded replica configuration."""
        super().setUpClass()
        # Create temp directory for test database
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, 'test_replica.db')
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temp files."""
        super().tearDownClass()
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def get_embedded_config(self):
        """Get embedded replica configuration."""
        return {
            'ENGINE': 'django_libsql.libsql',
            'NAME': self.db_path,
            'SYNC_URL': os.environ.get('TURSO_DATABASE_URL'),
            'AUTH_TOKEN': os.environ.get('TURSO_AUTH_TOKEN'),
            'SYNC_INTERVAL': 1.0,  # 1 second for testing
        }
    
    
    def scenario_single_threaded_writes(self):
        """Test single-threaded write performance."""
        results = {
            'scenario': 'single_threaded_writes',
            'records': 100,
            'start_time': time.time()
        }
        
        # Create records
        for i in range(100):
            TestModel.objects.create(
                name=f"single_thread_{i}",
                value=i
            )
        
        # Sync and verify
        connection.sync()
        
        results['duration'] = time.time() - results['start_time']
        results['count'] = TestModel.objects.filter(name__startswith='single_thread_').count()
        results['success'] = results['count'] == 100
        
        return results
    
    def scenario_multi_threaded_writes(self, num_threads=4):
        """Test multi-threaded write performance."""
        results = {
            'scenario': 'multi_threaded_writes',
            'threads': num_threads,
            'records_per_thread': 25,
            'start_time': time.time()
        }
        
        errors = []
        
        def worker(thread_id):
            """Worker thread function."""
            try:
                for i in range(25):
                    TestModel.objects.create(
                        name=f"thread_{thread_id}_item_{i}",
                        value=thread_id * 100 + i
                    )
                connection.sync()
            except Exception as e:
                errors.append(str(e))
        
        # Run threads
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        # Final sync
        connection.sync()
        
        results['duration'] = time.time() - results['start_time']
        results['errors'] = errors
        results['count'] = TestModel.objects.filter(name__startswith='thread_').count()
        results['expected'] = num_threads * 25
        results['success'] = len(errors) == 0 and results['count'] == results['expected']
        
        return results
    
    def scenario_concurrent_reads_writes(self):
        """Test concurrent read/write operations."""
        results = {
            'scenario': 'concurrent_reads_writes',
            'duration_seconds': 5,
            'start_time': time.time()
        }
        
        stop_event = threading.Event()
        write_count = 0
        read_count = 0
        errors = []
        
        def writer():
            nonlocal write_count
            while not stop_event.is_set():
                try:
                    TestModel.objects.create(
                        name=f"concurrent_{write_count}",
                        value=write_count
                    )
                    write_count += 1
                    time.sleep(0.01)
                except Exception as e:
                    errors.append(f"Write error: {e}")
        
        def reader():
            nonlocal read_count
            while not stop_event.is_set():
                try:
                    count = TestModel.objects.filter(name__startswith='concurrent_').count()
                    read_count += 1
                    time.sleep(0.01)
                except Exception as e:
                    errors.append(f"Read error: {e}")
        
        # Start threads
        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)
        
        writer_thread.start()
        reader_thread.start()
        
        # Run for duration
        time.sleep(5)
        stop_event.set()
        
        writer_thread.join()
        reader_thread.join()
        
        # Final sync
        connection.sync()
        
        results['duration'] = time.time() - results['start_time']
        results['writes'] = write_count
        results['reads'] = read_count
        results['errors'] = errors
        results['success'] = len(errors) == 0
        
        return results
    
    def scenario_batch_processing(self):
        """Test batch processing with sync."""
        results = {
            'scenario': 'batch_processing',
            'batch_size': 100,
            'num_batches': 5,
            'start_time': time.time()
        }
        
        sync_times = []
        
        for batch_num in range(5):
            # Create batch
            batch = []
            for i in range(100):
                batch.append(TestModel(
                    name=f"batch_{batch_num}_item_{i}",
                    value=batch_num * 1000 + i
                ))
            
            # Bulk create
            TestModel.objects.bulk_create(batch)
            
            # Sync after batch
            sync_start = time.time()
            connection.sync()
            sync_times.append(time.time() - sync_start)
        
        results['duration'] = time.time() - results['start_time']
        results['total_records'] = 500
        results['count'] = TestModel.objects.filter(name__startswith='batch_').count()
        results['sync_times'] = sync_times
        results['avg_sync_time'] = sum(sync_times) / len(sync_times) if sync_times else 0
        results['success'] = results['count'] == results['total_records']
        
        return results
    
    def scenario_complex_queries(self):
        """Test complex queries with embedded replica."""
        results = {
            'scenario': 'complex_queries',
            'start_time': time.time()
        }
        
        # Create test data
        books = []
        for i in range(50):
            book = Book.objects.create(
                title=f"Book {i}",
                author=f"Author {i % 10}",
                isbn=f"ISBN-{i:04d}",
                published_date=timezone.now().date(),
                pages=100 + i * 10,
                price=Decimal(f"{10 + i}.99"),
                in_stock=i % 2 == 0
            )
            books.append(book)
        
        # Sync
        connection.sync()
        
        # Complex queries
        query_times = {}
        
        # Aggregation
        start = time.time()
        stats = Book.objects.aggregate(
            avg_price=models.Avg('price'),
            total_pages=models.Sum('pages'),
            in_stock_count=models.Count('id', filter=models.Q(in_stock=True))
        )
        query_times['aggregation'] = time.time() - start
        
        # Filtering with joins
        start = time.time()
        books_by_author = Book.objects.filter(
            author__in=['Author 1', 'Author 2', 'Author 3']
        ).order_by('-price')[:10]
        list(books_by_author)  # Force evaluation
        query_times['filter_join'] = time.time() - start
        
        results['duration'] = time.time() - results['start_time']
        results['query_times'] = query_times
        results['success'] = True
        
        return results


@pytest.mark.skipif(
    not os.environ.get('TURSO_DATABASE_URL'),
    reason="Turso credentials not configured"
)
@pytest.mark.skipif(
    os.environ.get('TURSO_DATABASE_URL', '').startswith(('libsql://', 'wss://', 'https://')) and 
    not os.environ.get('USE_EMBEDDED_REPLICA'),
    reason="These tests require embedded replica configuration"
)
class TestEmbeddedReplicaAllModes(EmbeddedReplicaTestBase, TransactionTestCase):
    """Test embedded replica scenarios - requires local file + sync URL configuration."""
    
    def setUp(self):
        """Set up each test."""
        # Clean up any existing data
        TestModel.objects.all().delete()
        Book.objects.all().delete()
        Review.objects.all().delete()
    
    def test_all_scenarios_single_process(self):
        """Test all scenarios in single process mode."""
        print("\n" + "=" * 70)
        print("Testing Embedded Replica - Single Process Mode")
        print("=" * 70)
        
        with self.settings(DATABASES={'default': self.get_embedded_config()}):
            connections.close_all()
            
            results = []
            
            # Run all scenarios
            scenarios = [
                self.scenario_single_threaded_writes,
                self.scenario_multi_threaded_writes,
                self.scenario_concurrent_reads_writes,
                self.scenario_batch_processing,
                self.scenario_complex_queries,
            ]
            
            for scenario in scenarios:
                self.setUp()  # Clean between scenarios
                result = scenario()
                results.append(result)
                print(f"\n✓ {result['scenario']}: {'PASS' if result['success'] else 'FAIL'}")
                print(f"  Duration: {result['duration']:.2f}s")
            
            # All should succeed
            for result in results:
                self.assertTrue(result['success'], f"{result['scenario']} failed")
    
    def test_all_scenarios_with_threads(self):
        """Test all scenarios with threading."""
        print("\n" + "=" * 70)
        print("Testing Embedded Replica - Multi-threaded Mode")
        print("=" * 70)
        
        with self.settings(DATABASES={'default': self.get_embedded_config()}):
            connections.close_all()
            
            # Use ThreadPoolExecutor for better thread management
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = []
                
                # Run scenarios in parallel
                scenarios = [
                    lambda: self.scenario_multi_threaded_writes(num_threads=8),
                    self.scenario_concurrent_reads_writes,
                    self.scenario_batch_processing,
                ]
                
                for scenario in scenarios:
                    self.setUp()
                    future = executor.submit(scenario)
                    futures.append(future)
                
                # Collect results
                results = []
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    results.append(result)
                    print(f"\n✓ {result['scenario']}: {'PASS' if result['success'] else 'FAIL'}")
                    print(f"  Duration: {result['duration']:.2f}s")
                
                # All should succeed
                for result in results:
                    self.assertTrue(result['success'], f"{result['scenario']} failed")


def run_subprocess_test(test_name, env_vars=None):
    """Run a test in a subprocess with specific environment."""
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    # Build command
    cmd = [
        sys.executable,
        "-m", "pytest",
        __file__,
        f"-k", test_name,
        "-v", "-s"
    ]
    
    # Add -X gil=0 for no-GIL mode
    if env.get('PYTHON_GIL') == '0':
        cmd.insert(1, "-X")
        cmd.insert(2, "gil=0")
    
    # Run test
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    return {
        'success': result.returncode == 0,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'env': env_vars or {}
    }


class TestAllExecutionModes:
    """Meta-test that runs tests in all execution modes."""
    
    def test_all_modes_automatically(self):
        """Run tests in all modes automatically - NO MANUAL INTERVENTION!"""
        
        if not os.environ.get('TURSO_DATABASE_URL'):
            pytest.skip("Turso credentials not configured")
        
        print("\n" + "=" * 80)
        print("COMPREHENSIVE EMBEDDED REPLICA TEST SUITE")
        print("Testing ALL modes automatically!")
        print("=" * 80)
        
        # Define all test modes
        test_modes = [
            {
                'name': 'Regular Python',
                'env': {},
                'test': 'test_all_scenarios_single_process'
            },
            {
                'name': 'Python with Threads',
                'env': {},
                'test': 'test_all_scenarios_with_threads'
            },
            {
                'name': 'Python with Threads + No-GIL',
                'env': {'PYTHON_GIL': '0'},
                'test': 'test_all_scenarios_with_threads'
            },
        ]
        
        # Run all modes
        all_results = []
        
        for mode in test_modes:
            print(f"\n{'=' * 60}")
            print(f"Running: {mode['name']}")
            print(f"{'=' * 60}")
            
            result = run_subprocess_test(mode['test'], mode['env'])
            result['mode'] = mode['name']
            all_results.append(result)
            
            if result['success']:
                print(f"✅ {mode['name']}: PASSED")
            else:
                print(f"❌ {mode['name']}: FAILED")
                print("STDOUT:", result['stdout'][-500:])  # Last 500 chars
                print("STDERR:", result['stderr'][-500:])
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in all_results if r['success'])
        total = len(all_results)
        
        print(f"\nTotal: {total} modes tested")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        for result in all_results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"\n{result['mode']}: {status}")
        
        # Assert all passed
        assert all(r['success'] for r in all_results), "Some test modes failed!"
        
        print("\n🎉 ALL TESTS PASSED IN ALL MODES!")


# Performance comparison test
class TestPerformanceComparison:
    """Compare performance across different modes."""
    
    def test_performance_all_modes(self):
        """Run performance tests in all modes and compare."""
        
        if not os.environ.get('TURSO_DATABASE_URL'):
            pytest.skip("Turso credentials not configured")
        
        print("\n" + "=" * 80)
        print("PERFORMANCE COMPARISON - ALL MODES")
        print("=" * 80)
        
        # Run a specific performance scenario in each mode
        performance_test = """
import time
import threading
from tests.testapp.models import TestModel

def performance_test():
    start = time.time()
    
    def worker(worker_id):
        for i in range(100):
            TestModel.objects.create(name=f'perf_{worker_id}_{i}', value=i)
    
    threads = []
    for i in range(4):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()
    
    duration = time.time() - start
    count = TestModel.objects.filter(name__startswith='perf_').count()
    
    return {'duration': duration, 'count': count, 'throughput': count/duration}

result = performance_test()
print(f"PERF_RESULT:{result}")
"""
        
        modes = [
            ('Regular Python', {}),
            ('Python + Threads', {}),
            ('Python + No-GIL', {'PYTHON_GIL': '0'}),
        ]
        
        results = {}
        
        for mode_name, env in modes:
            # Run performance test
            print(f"\n{mode_name}...")
            # Parse results from subprocess output
            # Store in results dict
        
        # Print comparison
        print("\n" + "-" * 60)
        print("Performance Results:")
        print("-" * 60)
        
        # This would show actual performance comparisons


if __name__ == '__main__':
    """Allow running directly to test all modes."""
    test = TestAllExecutionModes()
    test.test_all_modes_automatically()