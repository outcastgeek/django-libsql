"""
Shared cleanup functionality for all example apps.
Drops ALL tables including Django's auth, admin, contenttypes, and sessions.
"""

from django.db import connection


def clean_database(stdout, app_prefix=None):
    """
    Clean all tables from the database.
    
    Args:
        stdout: Django command stdout for output
        app_prefix: Optional app prefix to include in cleanup (e.g., 'todo', 'blog')
    """
    stdout.write(f"🧹 Cleaning up {app_prefix + ' app' if app_prefix else 'all'} data...")
    
    with connection.cursor() as cursor:
        # Disable foreign key constraints for cleanup
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Get ALL tables except SQLite internal tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        all_tables = cursor.fetchall()
        
        if all_tables:
            # Drop ALL tables - we want a completely clean database
            for table in all_tables:
                table_name = table[0]
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                stdout.write(f"   Dropped {table_name}")
            stdout.write(f"   Total tables dropped: {len(all_tables)}")
        else:
            stdout.write("   No tables found - database is already clean")
        
        # Re-enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        connection.commit()
        
    stdout.write("✓ Cleanup complete - database is now completely empty!")