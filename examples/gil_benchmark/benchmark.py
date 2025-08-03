#!/usr/bin/env python
"""
No-GIL Performance Benchmark for django-libsql

This script demonstrates the performance benefits of Python 3.13's no-GIL mode
when using django-libsql with Turso for concurrent database operations.

Usage:
    # With GIL (default):
    python benchmark.py

    # Without GIL (Python 3.13+):
    PYTHON_GIL=0 python -X gil=0 benchmark.py
"""

import os
import sys
import time
import threading
import concurrent.futures
from decimal import Decimal
from datetime import datetime, date
import statistics

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

import django

django.setup()

from django.db import models, connections, transaction
from django.db.models import F
from django.utils import timezone


# Check GIL status
def is_gil_disabled():
    """Check if GIL is disabled."""
    try:
        import _thread

        return not _thread._is_gil_enabled()
    except (ImportError, AttributeError):
        return os.environ.get("PYTHON_GIL", "1") == "0"


# Define models for benchmarking
class BenchmarkRecord(models.Model):
    """Model for benchmark data."""

    name = models.CharField(max_length=100)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        app_label = "gil_benchmark"
        db_table = "benchmark_record"
        indexes = [
            models.Index(fields=["category", "-timestamp"]),
            models.Index(fields=["name"]),
        ]


class BenchmarkResult(models.Model):
    """Store benchmark results."""

    test_name = models.CharField(max_length=100)
    gil_enabled = models.BooleanField()
    num_threads = models.IntegerField()
    num_operations = models.IntegerField()
    duration_seconds = models.FloatField()
    operations_per_second = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "gil_benchmark"
        db_table = "benchmark_result"


class Benchmark:
    """Main benchmark class."""

    def __init__(self):
        self.gil_status = not is_gil_disabled()
        print(f"\n{'=' * 60}")
        print(f"Django-libSQL No-GIL Performance Benchmark")
        print(f"GIL Status: {'ENABLED' if self.gil_status else 'DISABLED'}")
        print(f"Python Version: {sys.version.split()[0]}")
        print(f"{'=' * 60}\n")

    def setup(self):
        """Create tables if they don't exist."""
        from django.db import connection

        with connection.schema_editor() as schema_editor:
            try:
                schema_editor.create_model(BenchmarkRecord)
                schema_editor.create_model(BenchmarkResult)
            except Exception:
                pass  # Tables already exist

    def cleanup(self):
        """Clean up test data."""
        BenchmarkRecord.objects.all().delete()

    def run_all_benchmarks(self):
        """Run all benchmark tests."""
        self.setup()

        benchmarks = [
            ("Sequential Writes", self.benchmark_sequential_writes),
            ("Concurrent Writes", self.benchmark_concurrent_writes),
            ("Sequential Reads", self.benchmark_sequential_reads),
            ("Concurrent Reads", self.benchmark_concurrent_reads),
            ("Mixed Operations", self.benchmark_mixed_operations),
            ("Complex Queries", self.benchmark_complex_queries),
            ("Batch Operations", self.benchmark_batch_operations),
            ("Transaction Heavy", self.benchmark_transactions),
        ]

        results = []
        for name, benchmark_func in benchmarks:
            print(f"\nRunning: {name}")
            print("-" * 40)
            result = benchmark_func()
            results.append((name, result))
            self.cleanup()

        self.print_summary(results)

    def benchmark_sequential_writes(self, num_operations=1000):
        """Benchmark sequential write operations."""
        start_time = time.perf_counter()

        for i in range(num_operations):
            BenchmarkRecord.objects.create(
                name=f"seq_write_{i}",
                value=Decimal(str(i * 10.5)),
                category="sequential",
                metadata={"index": i, "type": "write"},
            )

        duration = time.perf_counter() - start_time
        ops_per_sec = num_operations / duration

        print(f"Sequential writes: {ops_per_sec:.2f} ops/sec")

        self._save_result("sequential_writes", 1, num_operations, duration, ops_per_sec)
        return ops_per_sec

    def benchmark_concurrent_writes(self, num_threads=4, operations_per_thread=250):
        """Benchmark concurrent write operations."""

        def write_batch(thread_id):
            # Ensure each thread has its own connection
            connections.close_all()

            for i in range(operations_per_thread):
                BenchmarkRecord.objects.create(
                    name=f"concurrent_write_t{thread_id}_i{i}",
                    value=Decimal(str(thread_id * 1000 + i * 10.5)),
                    category=f"thread_{thread_id}",
                    metadata={"thread": thread_id, "index": i},
                )

        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(write_batch, i) for i in range(num_threads)]
            concurrent.futures.wait(futures)

        duration = time.perf_counter() - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_sec = total_operations / duration

        print(f"Concurrent writes ({num_threads} threads): {ops_per_sec:.2f} ops/sec")

        self._save_result(
            "concurrent_writes", num_threads, total_operations, duration, ops_per_sec
        )
        return ops_per_sec

    def benchmark_sequential_reads(self, num_operations=2000):
        """Benchmark sequential read operations."""
        # First create some data
        for i in range(100):
            BenchmarkRecord.objects.create(
                name=f"read_test_{i}", value=Decimal(str(i * 10)), category="read_test"
            )

        start_time = time.perf_counter()

        for i in range(num_operations):
            list(BenchmarkRecord.objects.filter(category="read_test").values())

        duration = time.perf_counter() - start_time
        ops_per_sec = num_operations / duration

        print(f"Sequential reads: {ops_per_sec:.2f} ops/sec")

        self._save_result("sequential_reads", 1, num_operations, duration, ops_per_sec)
        return ops_per_sec

    def benchmark_concurrent_reads(self, num_threads=4, operations_per_thread=500):
        """Benchmark concurrent read operations."""
        # First create some data
        for i in range(200):
            BenchmarkRecord.objects.create(
                name=f"concurrent_read_{i}",
                value=Decimal(str(i * 10)),
                category="concurrent_read",
            )

        def read_batch(thread_id):
            connections.close_all()

            for i in range(operations_per_thread):
                list(
                    BenchmarkRecord.objects.filter(category="concurrent_read").order_by(
                        "?"
                    )[:10]
                )

        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(read_batch, i) for i in range(num_threads)]
            concurrent.futures.wait(futures)

        duration = time.perf_counter() - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_sec = total_operations / duration

        print(f"Concurrent reads ({num_threads} threads): {ops_per_sec:.2f} ops/sec")

        self._save_result(
            "concurrent_reads", num_threads, total_operations, duration, ops_per_sec
        )
        return ops_per_sec

    def benchmark_mixed_operations(self, num_threads=4, operations_per_thread=200):
        """Benchmark mixed read/write operations."""
        # Seed with initial data
        for i in range(50):
            BenchmarkRecord.objects.create(
                name=f"mixed_{i}", value=Decimal(str(i * 100)), category="mixed"
            )

        def mixed_operations(thread_id):
            connections.close_all()

            for i in range(operations_per_thread):
                if i % 3 == 0:  # Write
                    BenchmarkRecord.objects.create(
                        name=f"mixed_t{thread_id}_i{i}",
                        value=Decimal(str(thread_id * 1000 + i)),
                        category="mixed",
                    )
                elif i % 3 == 1:  # Read
                    list(BenchmarkRecord.objects.filter(category="mixed")[:5])
                else:  # Update
                    record = (
                        BenchmarkRecord.objects.filter(category="mixed")
                        .order_by("?")
                        .first()
                    )
                    if record:
                        record.value = F("value") * Decimal("1.1")
                        record.save()

        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(mixed_operations, i) for i in range(num_threads)]
            concurrent.futures.wait(futures)

        duration = time.perf_counter() - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_sec = total_operations / duration

        print(f"Mixed operations ({num_threads} threads): {ops_per_sec:.2f} ops/sec")

        self._save_result(
            "mixed_operations", num_threads, total_operations, duration, ops_per_sec
        )
        return ops_per_sec

    def benchmark_complex_queries(self, num_threads=4, operations_per_thread=100):
        """Benchmark complex query operations."""
        # Create hierarchical data
        categories = ["electronics", "books", "clothing", "food", "toys"]
        for cat in categories:
            for i in range(50):
                BenchmarkRecord.objects.create(
                    name=f"{cat}_{i}",
                    value=Decimal(str(i * 10 + len(cat))),
                    category=cat,
                    metadata={
                        "subcategory": f"sub_{i % 5}",
                        "rating": i % 5 + 1,
                        "in_stock": i % 2 == 0,
                    },
                )

        def complex_queries(thread_id):
            connections.close_all()

            for i in range(operations_per_thread):
                # Aggregation query
                result = BenchmarkRecord.objects.filter(
                    category__in=categories[:3]
                ).aggregate(
                    avg_value=models.Avg("value"),
                    max_value=models.Max("value"),
                    count=models.Count("id"),
                )

                # Grouping query
                grouped = (
                    BenchmarkRecord.objects.values("category")
                    .annotate(total=models.Sum("value"), count=models.Count("id"))
                    .order_by("-total")[:3]
                )

                list(grouped)  # Force evaluation

        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(complex_queries, i) for i in range(num_threads)]
            concurrent.futures.wait(futures)

        duration = time.perf_counter() - start_time
        total_operations = (
            num_threads * operations_per_thread * 2
        )  # Two queries per iteration
        ops_per_sec = total_operations / duration

        print(f"Complex queries ({num_threads} threads): {ops_per_sec:.2f} ops/sec")

        self._save_result(
            "complex_queries", num_threads, total_operations, duration, ops_per_sec
        )
        return ops_per_sec

    def benchmark_batch_operations(self, num_threads=4, batch_size=100):
        """Benchmark batch insert operations."""

        def batch_insert(thread_id):
            connections.close_all()

            records = [
                BenchmarkRecord(
                    name=f"batch_t{thread_id}_i{i}",
                    value=Decimal(str(thread_id * 10000 + i)),
                    category=f"batch_{thread_id}",
                    metadata={"batch": thread_id, "index": i},
                )
                for i in range(batch_size)
            ]

            BenchmarkRecord.objects.bulk_create(records)

        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(batch_insert, i) for i in range(num_threads)]
            concurrent.futures.wait(futures)

        duration = time.perf_counter() - start_time
        total_operations = num_threads * batch_size
        ops_per_sec = total_operations / duration

        print(
            f"Batch operations ({num_threads} threads, {batch_size} per batch): {ops_per_sec:.2f} ops/sec"
        )

        self._save_result(
            "batch_operations", num_threads, total_operations, duration, ops_per_sec
        )
        return ops_per_sec

    def benchmark_transactions(self, num_threads=4, operations_per_thread=50):
        """Benchmark transaction-heavy operations."""

        def transaction_operations(thread_id):
            connections.close_all()

            for i in range(operations_per_thread):
                with transaction.atomic():
                    # Create parent record
                    parent = BenchmarkRecord.objects.create(
                        name=f"parent_t{thread_id}_i{i}",
                        value=Decimal(str(thread_id * 1000 + i * 100)),
                        category="parent",
                    )

                    # Create related records
                    for j in range(5):
                        BenchmarkRecord.objects.create(
                            name=f"child_t{thread_id}_i{i}_j{j}",
                            value=Decimal(str(j * 10)),
                            category="child",
                            metadata={"parent_id": parent.id},
                        )

                    # Update parent with sum
                    child_sum = (
                        BenchmarkRecord.objects.filter(
                            category="child", metadata__parent_id=parent.id
                        ).aggregate(total=models.Sum("value"))["total"]
                        or 0
                    )

                    parent.value = Decimal(str(child_sum))
                    parent.save()

        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(transaction_operations, i) for i in range(num_threads)
            ]
            concurrent.futures.wait(futures)

        duration = time.perf_counter() - start_time
        total_operations = (
            num_threads * operations_per_thread * 7
        )  # Parent + 5 children + update
        ops_per_sec = total_operations / duration

        print(
            f"Transaction operations ({num_threads} threads): {ops_per_sec:.2f} ops/sec"
        )

        self._save_result(
            "transaction_operations",
            num_threads,
            total_operations,
            duration,
            ops_per_sec,
        )
        return ops_per_sec

    def _save_result(
        self, test_name, num_threads, num_operations, duration, ops_per_sec
    ):
        """Save benchmark result to database."""
        BenchmarkResult.objects.create(
            test_name=test_name,
            gil_enabled=self.gil_status,
            num_threads=num_threads,
            num_operations=num_operations,
            duration_seconds=duration,
            operations_per_second=ops_per_sec,
        )

    def print_summary(self, results):
        """Print benchmark summary."""
        print(f"\n{'=' * 60}")
        print(f"Benchmark Summary - GIL {'ENABLED' if self.gil_status else 'DISABLED'}")
        print(f"{'=' * 60}")
        print(f"{'Test Name':<25} {'Ops/Sec':>15} {'Speedup':>10}")
        print(f"{'-' * 60}")

        # Calculate speedup for concurrent vs sequential
        seq_writes = next((r[1] for r in results if r[0] == "Sequential Writes"), 0)
        conc_writes = next((r[1] for r in results if r[0] == "Concurrent Writes"), 0)
        seq_reads = next((r[1] for r in results if r[0] == "Sequential Reads"), 0)
        conc_reads = next((r[1] for r in results if r[0] == "Concurrent Reads"), 0)

        for name, ops_per_sec in results:
            speedup = ""
            if name == "Concurrent Writes" and seq_writes > 0:
                speedup = f"{conc_writes / seq_writes:.2f}x"
            elif name == "Concurrent Reads" and seq_reads > 0:
                speedup = f"{conc_reads / seq_reads:.2f}x"

            print(f"{name:<25} {ops_per_sec:>15.2f} {speedup:>10}")

        print(f"\n{'=' * 60}")
        print("\nNOTE: Run this benchmark with both GIL enabled and disabled")
        print("to see the performance difference:")
        print("\n  With GIL:    python benchmark.py")
        print("  Without GIL: PYTHON_GIL=0 python -X gil=0 benchmark.py")
        print(f"{'=' * 60}\n")


# Settings module for standalone execution
DATABASES = {
    "default": {
        "ENGINE": "django_libsql.libsql",
        "NAME": os.environ.get("TURSO_DATABASE_URL", "file:benchmark.db"),
        "AUTH_TOKEN": os.environ.get("TURSO_AUTH_TOKEN", ""),
        "SYNC_INTERVAL": float(os.environ.get("TURSO_SYNC_INTERVAL", "0.1")),
    }
}

SECRET_KEY = "benchmark-secret-key"
INSTALLED_APPS = ["gil_benchmark"]
USE_TZ = True


def main():
    """Main entry point for GIL benchmark."""
    benchmark = Benchmark()
    benchmark.run_all_benchmarks()


if __name__ == "__main__":
    main()
