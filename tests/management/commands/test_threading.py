"""
Test threading with django-libsql backend.
"""
import threading
import concurrent.futures
from decimal import Decimal
from datetime import date

from django.core.management.base import BaseCommand
from django.db import connections
from tests.testapp.models import Book


class Command(BaseCommand):
    help = 'Test threading with django-libsql'

    def handle(self, *args, **options):
        self.stdout.write("Testing threading with django-libsql...")
        
        # Clean up
        Book.objects.all().delete()
        
        def create_books(worker_id):
            """Create books in a thread."""
            # Ensure each thread has its own connection
            connections.close_all()
            
            try:
                for i in range(3):
                    book = Book.objects.create(
                        title=f"Thread_{worker_id}_Book_{i}",
                        author=f"Author_{worker_id}",
                        isbn=f"978-{worker_id:02d}-{i:02d}-00000-0",
                        published_date=date(2024, 1, 1),
                        pages=100 + i,
                        price=Decimal("29.99"),
                        in_stock=True
                    )
                    self.stdout.write(f"  Worker {worker_id}: Created book {book.id}")
                return True
            except Exception as e:
                self.stdout.write(f"  Worker {worker_id} ERROR: {e}")
                return False
        
        # Run with 4 threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_books, i) for i in range(4)]
            results = [f.result() for f in futures]
        
        successful = sum(1 for r in results if r)
        total_books = Book.objects.count()
        
        self.stdout.write(f"\nResults:")
        self.stdout.write(f"  Successful workers: {successful}/4")
        self.stdout.write(f"  Total books created: {total_books}")
        
        if successful == 4 and total_books == 12:
            self.stdout.write(self.style.SUCCESS("✅ Threading test PASSED!"))
        else:
            self.stdout.write(self.style.ERROR("❌ Threading test FAILED!"))
        
        # Cleanup
        Book.objects.all().delete()