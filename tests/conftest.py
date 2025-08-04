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

        # Force commit
        connection.commit()
        
        # Only sync for embedded replicas (not remote-only connections)
        if hasattr(connection, "sync") and connection.settings_dict.get("SYNC_URL"):
            try:
                connection.sync()
            except Exception:
                # Sync not available for this connection type
                pass
    except Exception as e:
        # Tables might not exist yet  
        pass


def _cleanup_test_database(verbose=True):
    """Clean up test artifacts from the database."""
    import libsql
    from django.conf import settings
    
    db_settings = settings.DATABASES.get('default', {})
    url = db_settings.get('NAME') or db_settings.get('SYNC_URL')
    token = db_settings.get('AUTH_TOKEN')
    
    if not url or not url.startswith(('libsql://', 'wss://', 'https://')):
        return
    
    if verbose:
        print("\n🧹 Cleaning test database...")
    
    try:
        conn = libsql.connect(url, auth_token=token)
        cursor = conn.cursor()
        
        # Disable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Get all tables except SQLite internal tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        all_tables = [t[0] for t in cursor.fetchall()]
        
        # Drop ALL tables for complete cleanup
        tables_dropped = 0
        for table in all_tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            tables_dropped += 1
        
        # Re-enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        conn.close()
        
        if verbose:
            print(f"✓ Dropped {tables_dropped} tables")
            print("✓ Database cleanup complete - all tables removed!")
    
    except Exception as e:
        if verbose:
            print(f"Warning: Database cleanup failed: {e}")


@pytest.fixture(scope="session", autouse=True)
def cleanup_database_before_and_after_tests(request):
    """Clean up all test artifacts BEFORE and AFTER the entire test session."""
    # Clean BEFORE tests start
    _cleanup_test_database()
    
    # Register cleanup to run AFTER all tests
    request.addfinalizer(_cleanup_test_database)
