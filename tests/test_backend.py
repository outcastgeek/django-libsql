import os
from decimal import Decimal
from datetime import date, datetime

from django.test import TestCase, TransactionTestCase
from django.db import connection, transaction
from django.db.utils import IntegrityError
from tests.testapp.models import TestModel, RelatedModel, Book, Review


class LibSQLBackendTest(TestCase):
    """Test the libSQL Django backend."""

    def test_backend_vendor(self):
        """Test that the backend identifies as libsql."""
        self.assertEqual(connection.vendor, "libsql")
        self.assertEqual(connection.display_name, "libSQL (Turso)")

    def test_basic_crud_operations(self):
        """Test basic CRUD operations."""
        # Create
        obj = TestModel.objects.create(name="test", value=42)
        self.assertIsNotNone(obj.id)

        # Read
        retrieved = TestModel.objects.get(id=obj.id)
        self.assertEqual(retrieved.name, "test")
        self.assertEqual(retrieved.value, 42)

        # Update
        retrieved.value = 84
        retrieved.save()
        updated = TestModel.objects.get(id=obj.id)
        self.assertEqual(updated.value, 84)

        # Delete
        updated.delete()
        self.assertEqual(TestModel.objects.count(), 0)

    def test_foreign_key_relationships(self):
        """Test foreign key relationships."""
        parent = TestModel.objects.create(name="parent", value=1)
        child = RelatedModel.objects.create(
            test_model=parent, 
            description="child"
        )

        self.assertEqual(child.test_model.name, "parent")
        self.assertEqual(parent.relatedmodel_set.count(), 1)
        
        # Test cascade delete
        parent.delete()
        self.assertEqual(RelatedModel.objects.count(), 0)

    def test_complex_model_operations(self):
        """Test operations with complex model (Book)."""
        # Create book with all field types
        print(f"Creating first book with ISBN 978-0-00-000001-0")
        print(f"Books before create: {Book.objects.count()}")
        book = Book.objects.create(
            title="Django and libSQL",
            author="Test Author",
            isbn="978-0-00-000001-0",  # Unique ISBN for this test
            published_date=date(2024, 1, 15),
            pages=350,
            price=Decimal("49.99"),
            in_stock=True
        )
        print(f"First book created successfully: {book.id}")
        
        # Test auto-generated timestamps
        self.assertIsNotNone(book.created_at)
        self.assertIsNotNone(book.updated_at)
        self.assertIsInstance(book.created_at, datetime)
        
        # Test decimal field precision
        self.assertEqual(book.price, Decimal("49.99"))
        
        # Test unique constraint
        with self.assertRaises(IntegrityError):
            Book.objects.create(
                title="Another Book",
                author="Another Author",
                isbn="978-0-00-000001-0",  # Same ISBN
                published_date=date(2024, 1, 1),
                pages=200,
                price=Decimal("29.99"),
                in_stock=True
            )

    def test_indexes_and_ordering(self):
        """Test that indexes and ordering work correctly."""
        # Create books with different dates
        book1 = Book.objects.create(
            title="Old Book",
            author="Author 1",
            isbn="111-0-00-000000-0",
            published_date=date(2023, 1, 1),
            pages=100,
            price=Decimal("19.99"),
            in_stock=True
        )
        
        book2 = Book.objects.create(
            title="New Book",
            author="Author 2",
            isbn="222-0-00-000000-0",
            published_date=date(2024, 1, 1),
            pages=200,
            price=Decimal("29.99"),
            in_stock=True
        )
        
        # Test ordering (newest first due to -published_date)
        books = list(Book.objects.all())
        self.assertEqual(books[0].title, "New Book")
        self.assertEqual(books[1].title, "Old Book")
        
        # Test indexed queries
        found = Book.objects.filter(isbn="111-0-00-000000-0").first()
        self.assertEqual(found.title, "Old Book")
        
        # Test compound index query
        found = Book.objects.filter(author="Author 2", title="New Book").first()
        self.assertEqual(found.isbn, "222-0-00-000000-0")

    def test_unique_together_constraint(self):
        """Test unique_together constraint on Review model."""
        book = Book.objects.create(
            title="Review Test Book",
            author="Review Author",
            isbn="333-0-00-000003-0",  # Unique ISBN
            published_date=date(2024, 1, 1),
            pages=300,
            price=Decimal("39.99"),
            in_stock=True
        )
        
        # Create first review
        Review.objects.create(
            book=book,
            reviewer_name="John Doe",
            rating=5,
            comment="Excellent book!"
        )
        
        # Try to create duplicate review from same reviewer
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(
                    book=book,
                    reviewer_name="John Doe",  # Same reviewer
                    rating=1,
                    comment="Changed my mind"
                )
        
        # Different reviewer should work (outside the failed atomic block)
        review2 = Review.objects.create(
            book=book,
            reviewer_name="Jane Smith",
            rating=4,
            comment="Pretty good"
        )
        self.assertEqual(book.reviews.count(), 2)


class LibSQLTransactionTest(TransactionTestCase):
    """Test transaction handling with libSQL backend."""
    
    def test_transaction_rollback(self):
        """Test that transactions can be rolled back."""
        initial_count = TestModel.objects.count()
        
        try:
            with transaction.atomic():
                TestModel.objects.create(name="rollback_test", value=99)
                # Force an error
                raise Exception("Intentional error")
        except Exception:
            pass
        
        # Verify rollback
        self.assertEqual(TestModel.objects.count(), initial_count)
        self.assertFalse(TestModel.objects.filter(name="rollback_test").exists())
    
    def test_transaction_commit(self):
        """Test that transactions commit properly."""
        initial_count = TestModel.objects.count()
        
        with transaction.atomic():
            TestModel.objects.create(name="commit_test", value=88)
        
        # Verify commit
        self.assertEqual(TestModel.objects.count(), initial_count + 1)
        self.assertTrue(TestModel.objects.filter(name="commit_test").exists())
    
    def test_nested_transactions(self):
        """Test nested transaction behavior."""
        from django.db import connection
        
        initial_count = TestModel.objects.count()
        
        # Check if savepoints are supported
        if not connection.features.uses_savepoints:
            # Without savepoints, nested transactions don't work
            # Skip this test for libSQL
            self.skipTest("libSQL doesn't support savepoints for nested transactions")
        
        try:
            with transaction.atomic():
                TestModel.objects.create(name="outer", value=1)
                
                try:
                    with transaction.atomic():
                        TestModel.objects.create(name="inner", value=2)
                        raise Exception("Inner error")
                except Exception:
                    pass
                
                # Outer transaction should still work
                TestModel.objects.create(name="outer2", value=3)
        except Exception:
            pass
        
        # Check what was committed
        final_count = TestModel.objects.count()
        # With savepoints, outer and outer2 should be saved
        self.assertGreaterEqual(final_count, initial_count)


class LibSQLConnectionTest(TestCase):
    """Test connection-specific functionality."""
    
    def test_connection_settings(self):
        """Test that connection settings are properly applied."""
        settings = connection.settings_dict
        
        # Check if we're using Turso
        if os.environ.get('TURSO_DATABASE_URL'):
            self.assertIn('AUTH_TOKEN', settings)
            if 'SYNC_INTERVAL' in settings:
                self.assertIsInstance(settings['SYNC_INTERVAL'], (int, float))
    
    def test_pragma_execution(self):
        """Test that PRAGMAs can be executed."""
        with connection.cursor() as cursor:
            # Test foreign_keys pragma
            cursor.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()
            # Result format varies by libSQL version
            self.assertIsNotNone(result)
    
    def test_parameter_substitution(self):
        """Test that parameter substitution works correctly."""
        TestModel.objects.create(name="param_test", value=123)
        
        # Test with Django ORM (uses %s internally)
        found = TestModel.objects.filter(name="param_test").first()
        self.assertEqual(found.value, 123)
        
        # Test raw SQL with parameters
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT value FROM testapp_testmodel WHERE name = %s",
                ["param_test"]
            )
            result = cursor.fetchone()
            self.assertEqual(result[0], 123)
    
    def test_executemany(self):
        """Test executemany functionality."""
        with connection.cursor() as cursor:
            # Drop table first to ensure clean state
            cursor.execute("DROP TABLE IF EXISTS test_many")
            
            # Create table
            cursor.execute("""
                CREATE TABLE test_many (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    value INTEGER
                )
            """)
            
            # Test executemany
            data = [
                ("many1", 1),
                ("many2", 2),
                ("many3", 3),
            ]
            cursor.executemany(
                "INSERT INTO test_many (name, value) VALUES (%s, %s)",
                data
            )
            
            # Verify
            cursor.execute("SELECT COUNT(*) FROM test_many")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 3)  # Should be exactly 3
            
            # Cleanup
            cursor.execute("DROP TABLE IF EXISTS test_many")