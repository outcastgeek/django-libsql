"""Create sample data sources for processor app."""

from django.core.management.base import BaseCommand
from processor.models import DataSource


class Command(BaseCommand):
    help = "Creates sample data sources for the processor app"

    def handle(self, *args, **options):
        self.stdout.write("Creating sample data sources...")

        # Create data sources
        sources = [
            {
                "name": "Sales Data API",
                "url": "https://api.example.com/sales",
                "api_key": "demo-key-sales-123",
            },
            {
                "name": "Customer Analytics Feed",
                "url": "https://api.example.com/customers",
                "api_key": "demo-key-customers-456",
            },
            {
                "name": "Product Inventory System",
                "url": "https://api.example.com/inventory",
                "api_key": "demo-key-inventory-789",
            },
            {
                "name": "Local CSV Import",
                "url": "",
                "api_key": "",
            },
        ]

        created_count = 0
        for source_data in sources:
            source, created = DataSource.objects.get_or_create(
                name=source_data["name"],
                defaults={
                    "url": source_data["url"],
                    "api_key": source_data["api_key"],
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(f"Created data source: {source.name}")
            else:
                self.stdout.write(f"Data source already exists: {source.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully created {created_count} new data sources.\n"
                f"Total data sources: {DataSource.objects.count()}"
            )
        )

        self.stdout.write(
            "\nYou can now:\n"
            "1. Visit the admin panel to manage data sources\n"
            "2. Go to the main page to create processing jobs\n"
            "3. Monitor job progress in real-time"
        )
