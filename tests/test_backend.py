from django.test import TestCase
from django.db import connection
from tests.testapp.models import TestModel, RelatedModel


class LibSQLBackendTest(TestCase):
    """Test the libSQL Django backend."""

    def test_backend_vendor(self):
        """Test that the backend identifies as libsql."""
        self.assertEqual(connection.vendor, "libsql")

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