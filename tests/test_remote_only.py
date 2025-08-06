"""
Tests for remote-only mode (direct Turso connection).
These tests should work with stream timeouts and handle them gracefully.
"""

import os
import time
import pytest
from django.db import connection
from django.test import TransactionTestCase

from tests.testapp.models import Book, Review


def is_remote_only():
    """Check if we're using remote-only mode."""
    from django.conf import settings
    return not bool(settings.DATABASES['default'].get('SYNC_URL'))


# Decorator to skip tests when not in remote-only mode
requires_remote_only = pytest.mark.skipif(
    not is_remote_only(),
    reason="This test requires remote-only mode (set USE_EMBEDDED_REPLICA=false)"
)


@requires_remote_only
class RemoteOnlyTestCase(TransactionTestCase):
    """Tests specific to remote-only Turso connections."""
    
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
    
    def test_basic_crud_operations(self):
        """Test basic CRUD operations work with remote-only connection."""
        # CREATE
        book = Book.objects.create(
            title="Remote Test Book",
            author="Remote Author",
            isbn="999-0-00-000001-0",
            published_date="2024-01-01",
            pages=200,
            price="29.99",
            in_stock=True
        )
        
        # READ
        retrieved = Book.objects.get(id=book.id)
        self.assertEqual(retrieved.title, "Remote Test Book")
        
        # UPDATE
        retrieved.pages = 250
        retrieved.save()
        
        # Verify update
        updated = Book.objects.get(id=book.id)
        self.assertEqual(updated.pages, 250)
        
        # DELETE
        updated.delete()
        self.assertEqual(Book.objects.filter(id=book.id).count(), 0)
    
    def test_stream_timeout_handling(self):
        """Test that stream timeouts are handled gracefully and operations recover."""
        # This test verifies that the backend can recover from stream timeouts
        # which are expected behavior with remote Turso connections
        
        # First, create some test data to ensure we have something to query
        initial_count = Book.objects.count()
        test_book = Book.objects.create(
            title="Stream Test Book",
            author="Stream Author",
            isbn="888-0-00-000001-0",
            published_date="2024-01-01",
            pages=100,
            price="19.99",
            in_stock=True
        )
        
        # Verify creation worked
        self.assertEqual(Book.objects.count(), initial_count + 1)
        
        # Now test that operations can handle stream timeouts
        successful_ops = 0
        timeout_count = 0
        max_attempts = 5
        
        for i in range(max_attempts):
            try:
                # Perform operations that might experience stream timeouts
                count = Book.objects.count()
                self.assertEqual(count, initial_count + 1, "Count should match expected value")
                
                # Try a more complex operation
                books = list(Book.objects.filter(title__contains="Stream"))
                self.assertEqual(len(books), 1, "Should find our test book")
                self.assertEqual(books[0].title, "Stream Test Book")
                
                successful_ops += 1
            except Exception as e:
                if "stream not found" in str(e) or "stream timeout" in str(e).lower():
                    timeout_count += 1
                    # This is expected behavior - the connection will be recreated
                    time.sleep(0.1)  # Brief pause before retry
                else:
                    # Unexpected error - clean up and re-raise
                    test_book.delete()
                    raise
        
        # Clean up
        test_book.delete()
        
        # Verify that at least some operations succeeded
        self.assertGreater(successful_ops, 0, 
                          f"At least one operation should succeed. Timeouts: {timeout_count}")
        
        # If we had timeouts, verify the backend recovered
        if timeout_count > 0:
            print(f"Handled {timeout_count} stream timeouts gracefully")
    
    def test_no_sync_available(self):
        """Test that sync() is not available in remote-only mode."""
        # This should raise an error
        with self.assertRaises(Exception) as context:
            connection.sync()
        
        # The error message should indicate sync is only for embedded replicas
        self.assertIn("Manual sync is only available for embedded replica connections", str(context.exception))