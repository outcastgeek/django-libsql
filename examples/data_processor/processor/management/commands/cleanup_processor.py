"""
Command to clean up processor app data from the database.
"""
import sys
from pathlib import Path
from django.core.management.base import BaseCommand

# Add examples directory to path to import shared_cleanup
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from shared_cleanup import clean_database


class Command(BaseCommand):
    help = "Clean up all database tables for a fresh start"

    def handle(self, *args, **options):
        clean_database(self.stdout, app_prefix='processor')
