"""
Cleanup script for test databases.
"""
import os
import sys
import libsql
from pathlib import Path


def cleanup_test_db():
    """Clean up test database."""
    # Get settings from environment
    url = os.environ.get('TURSO_DATABASE_URL')
    token = os.environ.get('TURSO_AUTH_TOKEN')
    
    if url and url.startswith(('libsql://', 'wss://', 'https://')):
        print("🧹 Cleaning remote database...")
        try:
            conn = libsql.connect(url, auth_token=token)
            cursor = conn.cursor()
            
            # Disable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            all_tables = [t[0] for t in cursor.fetchall()]
            
            # Build dependency order for tables
            # Django's tables have specific dependencies:
            # 1. Drop review/related tables first (they have FKs)
            # 2. Drop main model tables (book, testmodel)
            # 3. Drop auth/permission tables (they have complex relationships)
            # 4. Drop django system tables last
            
            # Define the order explicitly for Django tables
            drop_order = []
            system_tables = []
            app_tables = []
            
            for table in all_tables:
                if table.startswith('testapp_review') or table.startswith('testapp_related'):
                    drop_order.insert(0, table)  # Drop first - has FKs to other tables
                elif table.startswith('testapp_'):
                    app_tables.append(table)
                elif table.startswith('auth_') or table.startswith('django_'):
                    system_tables.append(table)
                else:
                    drop_order.append(table)
            
            # Final order: app tables with FKs, other app tables, then system tables
            ordered_tables = drop_order + app_tables + system_tables
            
            # Drop ALL tables including django_migrations to force migrations to re-run
            for table in ordered_tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"  ✓ Dropped table: {table}")
            
            # Re-enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            conn.commit()
            conn.close()
            
            print("✓ Database cleanup complete!")
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            # Re-raise the exception to fail loudly - NO EXCEPTION SWALLOWING!
            raise
    
    # Also remove local test database files
    test_dir = Path(__file__).parent
    test_db_files = [
        'test_replica.db',
        'test_replica.db-shm',
        'test_replica.db-wal',
        'test_replica.db.meta',
        'test_replica.db-info'
    ]
    
    for db_file in test_db_files:
        db_path = test_dir / db_file
        if db_path.exists():
            print(f"Removing {db_file}...")
            db_path.unlink()


if __name__ == "__main__":
    cleanup_test_db()