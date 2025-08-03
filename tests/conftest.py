"""
pytest configuration for django-libsql tests.
"""

import os
import sys
import django
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

# Setup Django
django.setup()

# Import Django's pytest plugin to use its database setup
import pytest
from pytest_django.plugin import _setup_django


# Override the Django test database setup to ensure migrations run
@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    """Override django_db_setup to ensure migrations are run."""
    from django.core.management import call_command
    from django.db import connection

    with django_db_blocker.unblock():
        # Create migrations if needed
        try:
            call_command("makemigrations", "testapp", verbosity=0, interactive=False)
        except Exception:
            pass

        # Run migrations
        call_command("migrate", verbosity=0, interactive=False)

        # Ensure connection is synced for libSQL
        if hasattr(connection, "sync"):
            try:
                connection.sync()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def reset_test_data(db):
    """Reset test data before each test to ensure isolation."""
    from tests.testapp.models import Book, Review, TestModel, RelatedModel
    from django.db import connection, transaction

    # Clear all data before each test
    try:
        with transaction.atomic():
            # Delete in correct order to avoid foreign key issues
            Review.objects.all().delete()
            Book.objects.all().delete()
            RelatedModel.objects.all().delete()
            TestModel.objects.all().delete()

        # Force commit and sync for Turso
        connection.commit()
        if hasattr(connection, "sync"):
            connection.sync()

        print(
            f"Test data cleaned - Books: {Book.objects.count()}, Reviews: {Review.objects.count()}"
        )
    except Exception as e:
        # Tables might not exist yet
        print(f"Warning: Could not clean test data: {e}")
        pass
