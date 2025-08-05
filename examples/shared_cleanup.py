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
    
    try:
        with connection.cursor() as cursor:
            # Disable foreign key constraints for cleanup
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Get ALL tables except SQLite internal tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            all_tables = cursor.fetchall()
            
            if all_tables:
                # First pass: Drop tables that depend on others
                dependent_tables = [
                    'django_admin_log',
                    'auth_user_user_permissions', 
                    'auth_user_groups',
                    'auth_group_permissions',
                    'auth_permission',
                ]
                
                # Add app-specific tables
                if app_prefix:
                    app_tables = [t[0] for t in all_tables if t[0].startswith(f"{app_prefix}_")]
                    dependent_tables.extend(app_tables)
                
                dropped_count = 0
                for table_name in dependent_tables:
                    if any(t[0] == table_name for t in all_tables):
                        try:
                            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                            stdout.write(f"   Dropped {table_name}")
                            dropped_count += 1
                        except Exception as e:
                            stdout.write(f"   Failed to drop {table_name}: {e}")
                
                # Second pass: Drop remaining tables
                for table in all_tables:
                    table_name = table[0]
                    if table_name not in dependent_tables:
                        try:
                            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                            stdout.write(f"   Dropped {table_name}")
                            dropped_count += 1
                        except Exception as e:
                            stdout.write(f"   Failed to drop {table_name}: {e}")
                
                stdout.write(f"   Total tables dropped: {dropped_count}")
            else:
                stdout.write("   No tables found - database is already clean")
            
            # Re-enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            connection.commit()
    except Exception as e:
        stdout.write(f"   Cleanup error: {e}")
        # Try to clean up in a different order to handle FK constraints
        try:
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys = OFF")
                # Drop tables in reverse dependency order
                tables_to_drop = [
                    'django_admin_log',
                    'auth_user_user_permissions', 
                    'auth_user_groups',
                    'auth_group_permissions',
                    'auth_permission',
                    'auth_user',
                    'auth_group',
                    'django_content_type',
                    'django_session',
                    'django_migrations',
                ]
                # Add app-specific tables
                if app_prefix:
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '{app_prefix}_%'")
                    app_tables = [row[0] for row in cursor.fetchall()]
                    tables_to_drop.extend(app_tables)
                
                for table_name in tables_to_drop:
                    try:
                        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                        stdout.write(f"   Dropped {table_name}")
                    except:
                        pass
                
                connection.commit()
                cursor.execute("PRAGMA foreign_keys = ON")
        except Exception as e2:
            stdout.write(f"   Fallback cleanup also failed: {e2}")
        
    stdout.write("✓ Cleanup complete - database is now completely empty!")