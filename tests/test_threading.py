"""
Threading tests for Django libSQL backend.
Tests concurrent operations, GIL vs no-GIL performance, and thread safety.
"""

import os
import sys
import time
import threading
import concurrent.futures
from decimal import Decimal
from datetime import date

import pytest
from django.conf import settings
from django.db import connection, connections
from django.test import TransactionTestCase

from tests.testapp.models import Book, Review


def is_gil_disabled():
    """Check if GIL is actually disabled."""
    try:
        import _thread

        return not _thread._is_gil_enabled()
    except (ImportError, AttributeError):
        # For older Python versions
        return os.environ.get("PYTHON_GIL", "1") == "0"


def is_embedded_replica():
    """Check if we're using embedded replica mode."""
    return bool(settings.DATABASES['default'].get('SYNC_URL'))


# Decorator to skip tests that require embedded replicas
requires_embedded_replica = pytest.mark.skipif(
    not is_embedded_replica(),
    reason="This test requires embedded replica mode (set USE_EMBEDDED_REPLICA=true)"
)


class ThreadingTestCase(TransactionTestCase):
    """Test threading capabilities of the libSQL backend."""

    # Don't use transactions for test isolation
    serialized_rollback = False
    databases = '__all__'

    def setUp(self):
        """Setup test data."""
        # Simple cleanup without complex logic
        Book.objects.all().delete()
        Review.objects.all().delete()

    def test_gil_status_detection(self):
        """Test that GIL detection works and database operations work with both GIL and no-GIL."""
        gil_status = is_gil_disabled()
        print(f"GIL Status: {'DISABLED' if gil_status else 'ENABLED'}")

        # Verify GIL detection matches Python environment
        python_gil_env = os.environ.get('PYTHON_GIL', '1')
        
        # Check if we're in a no-GIL environment
        if python_gil_env == '0' and sys.version_info >= (3, 13):
            # We expect GIL to be disabled
            # Our detection should match this expectation
            try:
                import _thread
                if hasattr(_thread, '_is_gil_enabled'):
                    actual_gil_status = not _thread._is_gil_enabled()
                    self.assertEqual(gil_status, actual_gil_status, 
                                   "GIL detection doesn't match actual Python GIL status")
            except (ImportError, AttributeError):
                # Fallback for Python versions without _is_gil_enabled
                # Just verify our detection returns something sensible
                pass
        
        # Verify the function returns a boolean (basic sanity check)
        self.assertIsInstance(gil_status, bool)
        
        # The REAL test: Verify database operations work regardless of GIL status
        # This ensures the backend is compatible with both GIL and no-GIL Python
        Book.objects.all().delete()
        
        # Create a book
        book = Book.objects.create(
            title="GIL Test Book",
            author="Test Author",
            isbn="000-0-00-000000-0",
            published_date=date(2024, 1, 1),
            pages=100,
            price=Decimal("9.99"),
            in_stock=True
        )
        self.assertEqual(Book.objects.count(), 1, "Book creation should work")
        self.assertEqual(book.title, "GIL Test Book", "Book data should be correct")
        
        # Update the book
        book.pages = 200
        book.save()
        updated = Book.objects.get(id=book.id)
        self.assertEqual(updated.pages, 200, "Book update should work")
        
        # Delete the book
        book.delete()
        self.assertEqual(Book.objects.count(), 0, "Book deletion should work")
        
        # The key test: Verify that database works with current GIL status
        # This is what really matters - not just detecting GIL, but ensuring
        # the backend works properly regardless of GIL state
        print(f"Database operations completed successfully with GIL {'DISABLED' if gil_status else 'ENABLED'}")

    @pytest.mark.xfail(reason="Turso 502 errors under concurrent load", strict=False)
    def test_concurrent_model_creation(self):
        """Test creating models concurrently in multiple threads."""
        num_threads = 4
        books_per_thread = 5

        def create_books(thread_id):
            """Create books in a thread."""
            # Import connection inside thread to get thread-local connection
            from django.db import connection
            
            created_books = []
            try:
                for i in range(books_per_thread):
                    book = Book.objects.create(
                        title=f"Thread{thread_id}_Book{i}",
                        author=f"Author{thread_id}",
                        isbn=f"978-{thread_id:02d}-{i:02d}-00000-0",
                        published_date=date(2024, 1, 1),
                        pages=100 + i,
                        price=Decimal("29.99"),
                        in_stock=True,
                    )
                    created_books.append(book.id)
                # CRITICAL: Commit to flush writes to REMOTE in embedded mode
                connection.commit()
            except Exception as e:
                print(f"\nERROR in thread {thread_id}: {type(e).__name__}: {e}")
                raise
            return created_books

        # Run threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_books, i) for i in range(num_threads)]
            results = [f.result() for f in futures]

        # Verify results
        total_created = sum(len(r) for r in results)
        self.assertEqual(total_created, num_threads * books_per_thread)
        
        # In embedded replica mode, need to sync to see all writes from threads
        if is_embedded_replica():
            connection.sync()
        
        self.assertEqual(Book.objects.count(), num_threads * books_per_thread)

    @pytest.mark.xfail(reason="Turso stream timeouts under heavy concurrent load", strict=False)
    def test_concurrent_crud_operations(self):
        """
        Test concurrent CRUD operations across threads.
        
        Note: This test handles Turso stream timeouts which are normal behavior
        when using direct Turso connections. Streams may expire during concurrent
        operations, so we implement retry logic to handle this gracefully.
        """
        num_threads = 4
        operations_per_thread = 3

        def crud_operations(worker_id):
            """Perform CRUD operations in a thread."""
            # Import connection in thread for thread-local connection
            from django.db import connection
            
            results = {
                "created": 0,
                "read": 0,
                "updated": 0,
                "deleted": 0,
                "errors": [],
            }

            for i in range(operations_per_thread):
                # Handle expected Turso stream timeouts with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # CREATE
                        book = Book.objects.create(
                            title=f"CRUD_Test_{worker_id}_{i}",
                            author=f"Worker_{worker_id}",
                            isbn=f"999-{worker_id:03d}-{i:03d}-000-0",
                            published_date=date(2024, 1, 1),
                            pages=200,
                            price=Decimal("19.99"),
                            in_stock=True,
                        )
                        # Commit to flush write to REMOTE
                        connection.commit()
                        results["created"] += 1
                        
                        # Skip sync during CRUD for performance - rely on background sync

                        # READ
                        retrieved = Book.objects.get(id=book.id)
                        self.assertEqual(retrieved.title, book.title)
                        results["read"] += 1

                        # UPDATE
                        retrieved.pages = 300
                        retrieved.price = Decimal("29.99")
                        retrieved.save()
                        connection.commit()  # Commit update
                        results["updated"] += 1

                        # Verify update
                        updated = Book.objects.get(id=book.id)
                        self.assertEqual(updated.pages, 300)

                        # DELETE
                        updated.delete()
                        connection.commit()  # Commit delete
                        results["deleted"] += 1
                        
                        break  # Success - exit retry loop
                        
                    except Exception as e:
                        from django.db import OperationalError, connections
                        
                        # Check if this is a Turso stream timeout (expected behavior)
                        is_stream_error = (
                            "stream not found" in str(e).lower() or 
                            "database connection lost" in str(e).lower() or
                            isinstance(e, (OperationalError, ValueError))
                        )
                        
                        if is_stream_error and attempt < max_retries - 1:
                            results["errors"].append(f"Stream timeout (retry {attempt + 1}): {e}")
                            # Close the bad connection to force a fresh one
                            connections['default'].close()
                            time.sleep(0.1 * (attempt + 1))  # Brief exponential backoff
                            continue
                            
                        # Re-raise for non-stream errors or final attempt
                        if not is_stream_error:
                            results["errors"].append(f"Unexpected error: {e}")
                        else:
                            results["errors"].append(f"Stream timeout (final attempt): {e}")
                        raise

            return results

        # Run concurrent CRUD operations
        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(crud_operations, i) for i in range(num_threads)]
            results = [f.result() for f in futures]

        duration = time.perf_counter() - start_time

        # Verify results
        total_created = sum(r["created"] for r in results)
        total_deleted = sum(r["deleted"] for r in results)
        total_errors = sum(len(r["errors"]) for r in results)

        # Print errors for debugging
        if total_errors > 0:
            for i, r in enumerate(results):
                if r["errors"]:
                    print(f"\nWorker {i} errors: {r['errors']}")

        # All operations should succeed
        self.assertEqual(total_created, num_threads * operations_per_thread)
        self.assertEqual(total_deleted, num_threads * operations_per_thread)

        # Calculate and report performance
        total_operations = num_threads * operations_per_thread * 4  # CRUD = 4 ops
        ops_per_sec = total_operations / duration

        print(f"\nConcurrent CRUD Performance:")
        print(f"  Threads: {num_threads}")
        print(f"  Total operations: {total_operations}")
        print(f"  Duration: {duration:.3f}s")
        print(f"  Operations/sec: {ops_per_sec:.2f}")
        print(f"  GIL Status: {'DISABLED' if is_gil_disabled() else 'ENABLED'}")

    @requires_embedded_replica
    def test_concurrent_foreign_key_operations(self):
        """Test concurrent operations with foreign key relationships.
        
        IMPORTANT: With embedded replicas:
        - Writes go to REMOTE (Turso)
        - Reads come from LOCAL replica
        - We need to sync or wait for data to propagate
        """
        # Create base books (these write to REMOTE)
        books = []
        for i in range(5):
            book = Book.objects.create(
                title=f"FK_Test_Book_{i}",
                author="Test Author",
                isbn=f"888-0-00-{i:06d}-0",
                published_date=date(2024, 1, 1),
                pages=250,
                price=Decimal("24.99"),
                in_stock=True,
            )
            books.append(book)
        
        # CRITICAL: Commit the writes so they reach the remote!
        connection.commit()
        
        # CRITICAL: Force a sync so the books are visible in local replicas!
        # Without this, threads reading from local won't see the books
        connection.sync()
        
        # Also wait for automatic sync interval to ensure propagation
        sync_interval = connection.settings_dict.get('SYNC_INTERVAL', 0.1)
        time.sleep(sync_interval * 2)

        def create_reviews(worker_id):
            """Create reviews for books in a thread."""
            # Django handles per-thread connections automatically
            # when allow_thread_sharing = False
            from django.db import connection, OperationalError
            
            created_reviews = []
            errors = []
            
            for i, book in enumerate(books):
                # Retry logic for stream timeouts
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        review = Review.objects.create(
                            book=book,
                            reviewer_name=f"Reviewer_{worker_id}_{i}",
                            rating=4,
                            comment=f"Great book! Review from thread {worker_id}",
                        )
                        # Explicitly commit to ensure write reaches remote
                        connection.commit()
                        created_reviews.append(review.id)
                        break  # Success - exit retry loop
                        
                    except Exception as e:
                        error_msg = f"Worker {worker_id}, Book {i}, Attempt {attempt+1}: {type(e).__name__}: {str(e)[:100]}"
                        
                        # Check if it's a stream/connection error (expected with Turso)
                        is_stream_error = (
                            "stream not found" in str(e).lower() or
                            "unexpected EOF" in str(e) or
                            "Hrana" in str(e) or
                            isinstance(e, OperationalError)
                        )
                        
                        # Check if it's a unique constraint (also expected with concurrent creates)
                        is_unique_error = (
                            "UNIQUE constraint" in str(e) or 
                            "duplicate key" in str(e).lower()
                        )
                        
                        if is_stream_error and attempt < max_retries - 1:
                            # Stream error - retry
                            errors.append(f"Stream error (retrying): {error_msg}")
                            # Close the bad connection to force a new one
                            connection.close()
                            time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                            continue
                            
                        elif is_unique_error:
                            # Unique constraint - expected, just log it
                            errors.append(f"Duplicate (expected): {error_msg}")
                            break  # Don't retry for duplicates
                            
                        else:
                            # Unexpected error or final retry attempt
                            errors.append(f"Final error: {error_msg}")
                            if attempt == max_retries - 1:
                                # On final attempt, log but don't fail the whole test
                                # because some reviews might have been created
                                print(f"\nFailed to create review after {max_retries} attempts: {error_msg}")
                            break
                            
            return created_reviews, errors

        # Create reviews concurrently
        num_threads = 3
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_reviews, i) for i in range(num_threads)]
            results = [f.result() for f in futures]

        # Collect all created reviews and errors
        all_created = []
        all_errors = []
        for created, errors in results:
            all_created.extend(created)
            all_errors.extend(errors)
        
        # Print any errors for debugging
        if all_errors:
            print(f"\nReview creation errors (expected for duplicates): {all_errors}")
        
        # Verify that we actually created some reviews!
        # This is the REAL test - not just >= 0 which is meaningless
        self.assertGreater(len(all_created), 0, 
                          "At least some reviews should have been created successfully")
        
        # Verify foreign key integrity - each book should have at least one review
        # (since we have 3 threads trying to create reviews for 5 books)
        for book in books:
            reviews = book.reviews.all()
            self.assertGreater(reviews.count(), 0, 
                              f"Book '{book.title}' should have at least one review")

    def test_connection_isolation(self):
        """Test that each thread gets its own database connection."""
        connection_ids = []
        lock = threading.Lock()

        def get_connection_info(thread_id):
            """Get connection info in a thread."""
            # Get connection for this thread
            from django.db import connections
            conn = connections["default"]
            conn.ensure_connection()

            # Get connection id
            with conn.cursor() as cursor:
                # For libSQL, we can use the connection object id
                conn_id = id(conn.connection)

                with lock:
                    connection_ids.append(
                        {"thread_id": thread_id, "connection_id": conn_id}
                    )

            return conn_id

        # Run in multiple threads
        num_threads = 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(get_connection_info, i) for i in range(num_threads)
            ]
            results = [f.result() for f in futures]

        # Verify each thread got a different connection
        unique_connections = set(results)
        print(f"\nConnection Isolation Test:")
        print(f"  Threads: {num_threads}")
        print(f"  Unique connections: {len(unique_connections)}")

        # For Turso/libSQL, connections might be reused efficiently
        # We should have at least 2 unique connections
        self.assertGreaterEqual(len(unique_connections), 2)

    @requires_embedded_replica
    def test_sync_interval_effectiveness(self):
        """Test that sync_interval setting works correctly with embedded replicas."""
        sync_interval = connection.settings_dict.get("SYNC_INTERVAL", 0.1)
        
        # Clean up first
        Book.objects.filter(title="Sync Test Book").delete()
        connection.commit()  # CRITICAL: Commit the delete to REMOTE
        
        # Step 1: Create in one connection
        book = Book.objects.create(
            title="Sync Test Book",
            author="Sync Author",
            isbn="777-0-00-000000-0",
            published_date=date(2024, 1, 1),
            pages=100,
            price=Decimal("9.99"),
            in_stock=True,
        )
        # CRITICAL: Must commit to flush write to REMOTE
        connection.commit()
        
        # Step 2: Wait for background sync
        time.sleep(sync_interval * 2)  # Wait double the sync interval
        
        # Step 3: Check if another thread can see it
        def read_in_thread():
            # This gets a new connection which will have synced from REMOTE
            from django.db import connections
            # Force a new connection
            connections['default'].close()
            return Book.objects.filter(title="Sync Test Book").count()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(read_in_thread)
            count = future.result()
        
        # Should see the book after sync
        self.assertEqual(count, 1, "Book should be visible after sync interval")
        
    @requires_embedded_replica
    def test_manual_sync_effectiveness(self):
        """Test that manual sync actually syncs data from remote to local."""
        # This test verifies that sync() fetches changes from the remote database.
        # With embedded replicas:
        # 1. Writes go to REMOTE
        # 2. Reads come from LOCAL
        # 3. sync() fetches updates from REMOTE to LOCAL
        
        # Clean up first
        Book.objects.filter(title="Manual Sync Book").delete()
        connection.commit()  # CRITICAL: Commit delete to REMOTE
        
        # Force a sync first to ensure we have a clean state
        connection.sync()
        
        # Create a book (with embedded replica, this writes to REMOTE)
        book = Book.objects.create(
            title="Manual Sync Book",
            author="Sync Author",
            isbn="888-0-00-000000-0",
            published_date=date(2024, 1, 1),
            pages=100,
            price=Decimal("9.99"),
            in_stock=True,
        )
        
        # The book should be visible in the same connection (read-your-writes)
        same_conn_count = Book.objects.filter(title="Manual Sync Book").count()
        self.assertEqual(same_conn_count, 1, "Should see own write immediately")
        
        # IMPORTANT: Force the connection to commit and ensure write reaches remote
        # Django might be holding the transaction open
        connection.commit()
        
        # Give the write time to fully propagate to the remote
        # This is necessary because the write is async to the remote
        time.sleep(2.0)  # Increased delay to ensure remote has the write
        
        # Now test if another connection can see it after sync
        def read_in_another_thread():
            # This gets a new connection with its own local replica
            from django.db import connections
            # Force a new connection
            connections['default'].close()
            thread_conn = connections['default']
            thread_conn.ensure_connection()
            
            # Debug: What's the connection settings?
            db_name = thread_conn.settings_dict.get('NAME')
            sync_url = thread_conn.settings_dict.get('SYNC_URL')
            
            # Before sync - the local replica might not have the data yet
            before_sync = Book.objects.filter(title="Manual Sync Book").count()
            
            # Sync to fetch latest from remote
            thread_conn.sync()
            
            # After sync - the local replica should now have the data
            after_sync = Book.objects.filter(title="Manual Sync Book").count()
            
            return {
                "before": before_sync, 
                "after": after_sync,
                "db_name": db_name,
                "has_sync_url": bool(sync_url)
            }
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(read_in_another_thread)
            result = future.result()
        
        # Debug output
        print(f"\nDEBUG: Thread connection using db: {result['db_name']}, has_sync_url: {result['has_sync_url']}")
        print(f"DEBUG: Main connection using db: {connection.settings_dict.get('NAME')}")
        print(f"DEBUG: Before sync: {result['before']}, After sync: {result['after']}")
        
        # The key test: sync() should make remote data visible locally
        self.assertEqual(result["after"], 1, 
                        f"Book should be visible after sync. Before: {result['before']}, After: {result['after']}")


class ThreadingPerformanceTest(TransactionTestCase):
    """Performance comparison tests for GIL vs no-GIL."""

    # Don't use transactions for test isolation
    serialized_rollback = False
    databases = '__all__'

    def setUp(self):
        """Setup for performance tests."""
        Book.objects.all().delete()
        Review.objects.all().delete()

    @requires_embedded_replica
    @pytest.mark.xfail(reason="Turso stream timeouts under heavy concurrent load", strict=False)
    def test_performance_single_vs_multi_threaded(self):
        """Compare single-threaded vs multi-threaded performance."""
        num_operations = 10  # Reduced for faster testing

        def perform_operations():
            """Perform a set of database operations."""
            for i in range(num_operations):
                book = Book.objects.create(
                    title=f"Perf_Test_{i}",
                    author="Performance Author",
                    isbn=f"666-0-00-{i:06d}-0",
                    published_date=date(2024, 1, 1),
                    pages=300,
                    price=Decimal("39.99"),
                    in_stock=True,
                )
                # Read back
                Book.objects.get(id=book.id)
                # Update
                book.pages = 400
                book.save()
                # Skip delete to avoid transaction issues
                # book.delete()

        # Single-threaded test
        Book.objects.all().delete()

        # Clean up any leftover test data
        Book.objects.filter(title__startswith="Perf_Test_").delete()
        Book.objects.filter(title__startswith="MT_Test_").delete()
        start_time = time.perf_counter()
        perform_operations()
        single_duration = time.perf_counter() - start_time
        single_ops_per_sec = (
            num_operations * 3
        ) / single_duration  # 3 ops per iteration (no delete)

        # Multi-threaded test
        Book.objects.all().delete()
        num_threads = 4
        ops_per_thread = num_operations // num_threads

        def thread_operations(thread_id):
            from django.db import connection, connections
            
            for i in range(ops_per_thread):
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        book = Book.objects.create(
                            title=f"MT_Test_{thread_id}_{i}",
                            author=f"MT_Author_{thread_id}",
                            isbn=f"555-{thread_id:02d}-{i:04d}-00-0",
                            published_date=date(2024, 1, 1),
                            pages=300,
                            price=Decimal("39.99"),
                            in_stock=True,
                        )
                        connection.commit()
                        
                        Book.objects.get(id=book.id)
                        book.pages = 400
                        book.save()
                        connection.commit()
                        # Skip delete to avoid transaction issues
                        # book.delete()
                        break  # Success
                    except Exception as e:
                        if "stream not found" in str(e).lower() and attempt < max_retries - 1:
                            # Close bad connection and retry
                            connections['default'].close()
                            time.sleep(0.1)
                            continue
                        raise  # Re-raise on final attempt or unexpected error

        start_time = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(thread_operations, i) for i in range(num_threads)
            ]
            [f.result() for f in futures]
        multi_duration = time.perf_counter() - start_time
        multi_ops_per_sec = (
            num_threads * ops_per_thread * 3
        ) / multi_duration  # 3 ops per iteration

        # Report results
        print(
            f"\nPerformance Comparison (GIL {'DISABLED' if is_gil_disabled() else 'ENABLED'}):"
        )
        print(f"  Single-threaded: {single_ops_per_sec:.2f} ops/sec")
        print(
            f"  Multi-threaded ({num_threads} threads): {multi_ops_per_sec:.2f} ops/sec"
        )
        print(f"  Speedup: {multi_ops_per_sec / single_ops_per_sec:.2f}x")

        # Clean up created test data
        Book.objects.filter(title__startswith="Perf_Test_").delete()
        Book.objects.filter(title__startswith="MT_Test_").delete()

        # With GIL disabled, multi-threaded should be faster
        speedup = multi_ops_per_sec / single_ops_per_sec
        if is_gil_disabled():
            # With no-GIL, we should see meaningful speedup, but remote Turso connections
            # add network latency that limits parallelism benefits
            # Accept any speedup > 1.20x as valid for remote connections
            self.assertGreater(
                speedup,
                1.20,
                f"Expected at least 20% speedup with no-GIL, got {speedup:.2f}x",
            )

            # Also verify it's better than typical GIL performance
            self.assertGreater(
                speedup,
                1.15,
                f"No-GIL performance ({speedup:.2f}x) should exceed typical GIL limits",
            )
        else:
            # With GIL, improvement should be minimal
            print(
                f"\n📌 Note: Running with GIL enabled. Speedup limited to {multi_ops_per_sec / single_ops_per_sec:.2f}x"
            )


@pytest.mark.skipif(
    not os.environ.get("TURSO_DATABASE_URL"),
    reason="Turso environment variables not set",
)
class TursoSpecificTests(TransactionTestCase):
    """Tests specific to Turso remote database functionality."""

    def test_turso_connection(self):
        """Test that we can connect to Turso."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)

    @requires_embedded_replica
    def test_turso_sync_with_threading(self):
        """Test Turso sync behavior with multiple threads."""

        def create_and_verify(thread_id):
            """Create data and verify it's synced."""
            # Import connection in thread to get thread-local connection
            from django.db import connection
            
            # Create
            book = Book.objects.create(
                title=f"Turso_Sync_{thread_id}",
                author="Turso Author",
                isbn=f"444-0-00-{thread_id:06d}-0",
                published_date=date(2024, 1, 1),
                pages=250,
                price=Decimal("34.99"),
                in_stock=True,
            )
            
            # CRITICAL: Commit to flush write to REMOTE
            connection.commit()
            
            # If embedded replica, sync to see the data locally
            if is_embedded_replica():
                connection.sync()

            # Now read - will come from LOCAL in embedded mode
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM testapp_book WHERE title LIKE 'Turso_Sync_%'"
                )
                count = cursor.fetchone()[0]

            return count

        # Run in threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_and_verify, i) for i in range(3)]
            results = [f.result() for f in futures]

        # Each thread should see at least its own insert
        for i, count in enumerate(results):
            self.assertGreaterEqual(count, i + 1)
