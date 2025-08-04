"""
Command to clean up todo app data from the database.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Clean up all todo app tables and migration records"

    def handle(self, *args, **options):
        self.stdout.write("🧹 Cleaning up todo app data...")
        
        with connection.cursor() as cursor:
            # Disable foreign key constraints for cleanup
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Drop all todo tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'todo_%'")
            tables = cursor.fetchall()
            
            if tables:
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
                    self.stdout.write(f"   Dropped {table[0]}")
            else:
                self.stdout.write("   No todo tables found")
            
            # Clean migration records
            try:
                cursor.execute("DELETE FROM django_migrations WHERE app='todo'")
                if cursor.rowcount > 0:
                    self.stdout.write(f"   Deleted {cursor.rowcount} migration records")
            except Exception:
                pass
            
            # Re-enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            connection.commit()
            
        self.stdout.write(self.style.SUCCESS("✓ Cleanup complete!"))