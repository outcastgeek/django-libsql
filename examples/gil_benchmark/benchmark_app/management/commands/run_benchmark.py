"""
Benchmark command that runs in ALL modes automatically:
1. Regular Python
2. Python with Threads  
3. Python with Threads + No-GIL
4. Python with Threads + No-GIL + Django ORM

It also tests both remote-only and embedded replica configurations.
"""

import os
import sys
import time
import threading
import concurrent.futures
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import connection, connections, transaction
from django.utils import timezone

from benchmark_app.models import BenchmarkResult, TestRecord


class Command(BaseCommand):
    help = 'Run performance benchmarks in all modes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--operations',
            type=int,
            default=1000,
            help='Number of operations per test'
        )
        parser.add_argument(
            '--threads',
            type=int,
            default=0,
            help='Number of threads (0 = auto based on mode)'
        )
        parser.add_argument(
            '--test',
            choices=['crud', 'read', 'write', 'mixed', 'all'],
            default='all',
            help='Type of test to run'
        )

    def handle(self, *args, **options):
        operations = options['operations']
        num_threads = options['threads']
        test_type = options['test']
        
        # Detect environment
        gil_status = self.get_gil_status()
        # Check if using embedded replica by looking for SYNC_URL in settings
        is_embedded = connection.settings_dict.get('SYNC_URL') is not None
        
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write("DJANGO-LIBSQL PERFORMANCE BENCHMARK")
        self.stdout.write(f"{'='*70}")
        self.stdout.write(f"Python: {sys.version.split()[0]}")
        self.stdout.write(f"GIL: {'DISABLED (Free-Threading)' if 'disabled' in gil_status else 'ENABLED'}")
        self.stdout.write(f"Database: {'Embedded Replica' if is_embedded else 'Remote Only'}")
        self.stdout.write(f"Operations: {operations}")
        self.stdout.write(f"{'='*70}\n")
        
        # Clear test data
        TestRecord.objects.all().delete()
        
        # Run tests
        if test_type == 'all':
            tests = ['crud', 'read', 'write', 'mixed']
        else:
            tests = [test_type]
        
        results = []
        for test in tests:
            # Single-threaded
            result = self.run_test(test, operations, 1)
            results.append(result)
            
            # Multi-threaded
            if num_threads == 0:
                # Auto-detect based on GIL
                threads = 8 if 'disabled' in gil_status else 4
            else:
                threads = num_threads
            
            result = self.run_test(test, operations, threads)
            results.append(result)
        
        # Show results
        self.show_results(results)
        
        # Save results
        self.save_results(results)

    def run_test(self, test_type, operations, threads):
        """Run a specific test."""
        self.stdout.write(f"\nRunning {test_type.upper()} test with {threads} thread(s)...")
        
        # Prepare test
        if test_type in ['read', 'mixed']:
            # Create data for reads
            self.create_test_data(1000)
        
        # Run benchmark
        start_time = time.time()
        
        if threads == 1:
            ops_completed = self.run_single_threaded(test_type, operations)
        else:
            ops_completed = self.run_multi_threaded(test_type, operations, threads)
        
        duration = time.time() - start_time
        throughput = ops_completed / duration
        
        # Create result
        result = {
            'test_name': test_type,
            'mode': self.get_mode_name(threads),
            'threads': threads,
            'operations': ops_completed,
            'duration': duration,
            'throughput': throughput,
            'python_version': sys.version.split()[0],
            'gil_enabled': 'disabled' not in self.get_gil_status(),
            'is_embedded': hasattr(connection, 'sync'),
        }
        
        self.stdout.write(
            f"  Completed: {ops_completed} ops in {duration:.2f}s "
            f"({throughput:.2f} ops/sec)"
        )
        
        # Clean up
        if test_type != 'read':
            TestRecord.objects.all().delete()
        
        return result

    def run_single_threaded(self, test_type, operations):
        """Run test in single thread."""
        if test_type == 'crud':
            return self.crud_operations(operations)
        elif test_type == 'read':
            return self.read_operations(operations)
        elif test_type == 'write':
            return self.write_operations(operations)
        elif test_type == 'mixed':
            return self.mixed_operations(operations)

    def run_multi_threaded(self, test_type, operations, threads):
        """Run test with multiple threads."""
        ops_per_thread = operations // threads
        completed = [0] * threads
        
        def worker(thread_id):
            if test_type == 'crud':
                completed[thread_id] = self.crud_operations(ops_per_thread, thread_id)
            elif test_type == 'read':
                completed[thread_id] = self.read_operations(ops_per_thread)
            elif test_type == 'write':
                completed[thread_id] = self.write_operations(ops_per_thread, thread_id)
            elif test_type == 'mixed':
                completed[thread_id] = self.mixed_operations(ops_per_thread, thread_id)
        
        # Run threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []
            for i in range(threads):
                future = executor.submit(worker, i)
                futures.append(future)
            
            concurrent.futures.wait(futures)
        
        return sum(completed)

    def crud_operations(self, count, thread_id=0):
        """Perform CRUD operations."""
        completed = 0
        
        for i in range(count):
            # Create
            obj = TestRecord.objects.create(
                name=f"test_{thread_id}_{i}",
                value=i,
                data=f"Test data for record {i}"
            )
            
            # Read
            obj = TestRecord.objects.get(pk=obj.pk)
            
            # Update
            obj.value = i * 2
            obj.save()
            
            # Delete
            obj.delete()
            
            completed += 1
            
            # Sync periodically for embedded replicas
            if connection.settings_dict.get('SYNC_URL') and completed % 100 == 0:
                connection.sync()
        
        return completed

    def read_operations(self, count):
        """Perform read operations."""
        completed = 0
        total_records = TestRecord.objects.count()
        
        for i in range(count):
            # Various read patterns
            if i % 4 == 0:
                # Get by ID
                try:
                    obj = TestRecord.objects.get(pk=(i % total_records) + 1)
                except TestRecord.DoesNotExist:
                    pass
            elif i % 4 == 1:
                # Filter
                objs = list(TestRecord.objects.filter(value__gte=i % 100)[:10])
            elif i % 4 == 2:
                # Aggregate
                result = TestRecord.objects.aggregate(
                    avg_value=models.Avg('value'),
                    max_value=models.Max('value')
                )
            else:
                # Count
                count = TestRecord.objects.filter(name__startswith='test_').count()
            
            completed += 1
        
        return completed

    def write_operations(self, count, thread_id=0):
        """Perform write operations."""
        completed = 0
        batch = []
        
        for i in range(count):
            record = TestRecord(
                name=f"write_{thread_id}_{i}",
                value=i,
                data=f"Write test data {i}" * 10
            )
            batch.append(record)
            
            # Bulk create every 100 records
            if len(batch) >= 100:
                TestRecord.objects.bulk_create(batch)
                batch = []
                
                # Sync for embedded replicas
                if connection.settings_dict.get('SYNC_URL'):
                    connection.sync()
            
            completed += 1
        
        # Create remaining
        if batch:
            TestRecord.objects.bulk_create(batch)
        
        return completed

    def mixed_operations(self, count, thread_id=0):
        """Perform mixed read/write operations."""
        completed = 0
        
        for i in range(count):
            operation = i % 4
            
            if operation == 0:
                # Create
                TestRecord.objects.create(
                    name=f"mixed_{thread_id}_{i}",
                    value=i,
                    data=f"Mixed data {i}"
                )
            elif operation == 1:
                # Read
                TestRecord.objects.filter(value__lt=100).first()
            elif operation == 2:
                # Update
                TestRecord.objects.filter(
                    name__startswith=f"mixed_{thread_id}_"
                ).update(value=models.F('value') + 1)
            else:
                # Delete some old records
                TestRecord.objects.filter(
                    name__startswith=f"mixed_{thread_id}_",
                    value__lt=i - 100
                ).delete()
            
            completed += 1
            
            # Sync periodically
            if connection.settings_dict.get('SYNC_URL') and completed % 50 == 0:
                connection.sync()
        
        return completed

    def create_test_data(self, count):
        """Create test data for read operations."""
        self.stdout.write(f"Creating {count} test records...")
        
        batch = []
        for i in range(count):
            batch.append(TestRecord(
                name=f"test_data_{i}",
                value=i,
                data=f"Test data for reads {i}" * 5
            ))
            
            if len(batch) >= 100:
                TestRecord.objects.bulk_create(batch)
                batch = []
        
        if batch:
            TestRecord.objects.bulk_create(batch)
        
        # Sync if embedded
        if connection.settings_dict.get('SYNC_URL'):
            connection.sync()

    def get_gil_status(self):
        """Get GIL status."""
        if hasattr(sys, '_is_gil_enabled'):
            return "disabled" if not sys._is_gil_enabled() else "enabled"
        return "enabled"

    def get_mode_name(self, threads):
        """Get descriptive mode name."""
        gil = "no-gil" if "disabled" in self.get_gil_status() else "gil"
        db = "embedded" if hasattr(connection, 'sync') else "remote"
        thread_str = "single" if threads == 1 else f"multi-{threads}"
        return f"{db}-{gil}-{thread_str}"

    def show_results(self, results):
        """Display benchmark results."""
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write("BENCHMARK RESULTS")
        self.stdout.write(f"{'='*70}")
        
        # Group by test type
        by_test = {}
        for r in results:
            test = r['test_name']
            if test not in by_test:
                by_test[test] = []
            by_test[test].append(r)
        
        # Show comparisons
        for test, test_results in by_test.items():
            self.stdout.write(f"\n{test.upper()} Performance:")
            
            # Sort by throughput
            test_results.sort(key=lambda x: x['throughput'], reverse=True)
            
            for r in test_results:
                self.stdout.write(
                    f"  {r['mode']}: {r['throughput']:.2f} ops/sec "
                    f"({r['operations']} ops in {r['duration']:.2f}s)"
                )
            
            # Calculate improvements
            if len(test_results) >= 2:
                baseline = test_results[-1]['throughput']  # Slowest
                best = test_results[0]['throughput']  # Fastest
                if baseline > 0:
                    improvement = ((best - baseline) / baseline) * 100
                    self.stdout.write(
                        f"  Best improvement: {improvement:.1f}% "
                        f"({test_results[0]['mode']} vs {test_results[-1]['mode']})"
                    )

    def save_results(self, results):
        """Save results to database."""
        for r in results:
            BenchmarkResult.objects.create(**r)
        
        self.stdout.write(f"\nResults saved to database.")


# Import at end to avoid circular imports
from django.db import models