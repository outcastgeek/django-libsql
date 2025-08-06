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
    import os

    with django_db_blocker.unblock():
        # For embedded replica mode, we need to ensure tables exist
        is_embedded = os.environ.get('USE_EMBEDDED_REPLICA', 'False').lower() in ('true', '1', 'yes')
        
        # Always create migrations first
        call_command("makemigrations", "testapp", verbosity=0, interactive=False)
        
        # Check if tables already exist to avoid "table already exists" error
        connection.ensure_connection()
        
        # Try to check if migrations table exists
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='django_migrations'")
                has_migrations_table = cursor.fetchone() is not None
        except Exception as e:
            # If we can't check, assume no tables
            has_migrations_table = False
        
        # For embedded replica, we need special handling for migrations
        if is_embedded:
            # First, try to sync any existing tables from remote
            if hasattr(connection, "sync"):
                try:
                    connection.sync()
                except Exception as e:
                    # Only ignore if it's the expected error for no tables
                    if "no such table" not in str(e).lower():
                        raise  # Re-raise unexpected errors
            
            # Always use normal migrate for embedded replica too
            # The --run-syncdb flag causes issues with Django's built-in migrations
            call_command("migrate", verbosity=1, interactive=False)
            
            # After migrations, sync again to ensure LOCAL has all the tables
            if hasattr(connection, "sync"):
                try:
                    connection.sync()
                    connection.commit()
                except Exception as e:
                    print(f"Warning: Sync after migrations failed: {e}")
        else:
            # For remote-only mode, always use normal migrate
            # Django will handle creating tables if they don't exist
            call_command("migrate", verbosity=1, interactive=False)


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
        # Transaction automatically commits when exiting the atomic block
        
        # Only sync for embedded replicas (not remote-only connections)
        if hasattr(connection, "sync") and connection.settings_dict.get("SYNC_URL"):
            connection.sync()
    except Exception as e:
        # Only ignore if tables don't exist (first run) - all other errors should propagate
        if "no such table" not in str(e).lower():
            raise  # Re-raise any unexpected errors
        # Tables don't exist yet - this is fine, Django will create them


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
        # Re-raise to fail loudly - NO EXCEPTION SWALLOWING!
        raise


@pytest.fixture(scope="session", autouse=True)
def cleanup_database_before_and_after_tests(request):
    """Clean up all test artifacts BEFORE and AFTER the entire test session."""
    import os
    from pathlib import Path
    
    # For embedded replica mode, ALWAYS clean up local files BEFORE tests
    # This ensures we start fresh with an empty local replica
    base_dir = Path(__file__).resolve().parent
    replica_files = [
        base_dir / "test_replica.db",
        base_dir / "test_replica.db-wal",
        base_dir / "test_replica.db-shm",
        base_dir / "test_replica.db-info"
    ]
    for f in replica_files:
        if f.exists():
            f.unlink()
    
    # DON'T clean remote database here - it's cleaned by Makefile between modes
    # _cleanup_test_database()  # REMOVED - handled by Makefile
    
    # Register cleanup to run AFTER all tests
    def final_cleanup():
        # Only clean up local files, not remote
        for f in replica_files:
            if f.exists():
                f.unlink()
    
    request.addfinalizer(final_cleanup)
