"""
Command to clean up sensors app data from the database.
"""
import os
import sys
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

# Add examples directory to path to import shared_cleanup
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from shared_cleanup import clean_database


class Command(BaseCommand):
    help = "Clean up all database tables for a fresh start"

    def handle(self, *args, **options):
        # Clean the remote database
        clean_database(self.stdout, app_prefix='sensors')
        
        # If using embedded replica mode, also remove the local database file
        # Check if SYNC_URL is configured in settings (indicates embedded replica mode)
        if settings.DATABASES['default'].get('SYNC_URL'):
            local_db_path = Path(settings.BASE_DIR) / 'local_replica.db'
            
            # Remove all database-related files regardless of main db existence
            files_to_remove = [
                local_db_path,
                Path(str(local_db_path) + '-shm'),
                Path(str(local_db_path) + '-wal'), 
                Path(str(local_db_path) + '.meta'),
                Path(str(local_db_path) + '-info')
            ]
            
            for file_path in files_to_remove:
                if file_path.exists():
                    try:
                        self.stdout.write(f"   Removing file: {file_path.name}")
                        file_path.unlink()
                    except Exception as e:
                        self.stdout.write(f"   Failed to remove {file_path.name}: {e}")
