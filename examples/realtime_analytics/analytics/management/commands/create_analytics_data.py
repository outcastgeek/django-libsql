"""Create sample website for analytics tracking."""

from django.core.management.base import BaseCommand
from analytics.models import Website
import uuid


class Command(BaseCommand):
    help = "Creates sample websites for analytics tracking"

    def handle(self, *args, **options):
        self.stdout.write("Creating sample websites...")

        # Create websites
        websites = [
            {
                "domain": "example.com",
                "name": "Example Company Website",
            },
            {
                "domain": "blog.example.com",
                "name": "Example Blog",
            },
            {
                "domain": "shop.example.com",
                "name": "Example Shop",
            },
        ]

        created_count = 0
        for site_data in websites:
            website, created = Website.objects.get_or_create(
                domain=site_data["domain"],
                defaults={
                    "name": site_data["name"],
                    "tracking_id": str(uuid.uuid4())[:8],
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(f"Created website: {website.name}")
                self.stdout.write(f"  Domain: {website.domain}")
                self.stdout.write(f"  Tracking ID: {website.tracking_id}")
            else:
                self.stdout.write(f"Website already exists: {website.name}")
                self.stdout.write(f"  Tracking ID: {website.tracking_id}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully created {created_count} new websites.\n"
                f"Total websites: {Website.objects.count()}"
            )
        )

        # Show tracking script example
        first_website = Website.objects.first()
        if first_website:
            self.stdout.write(
                f"\nExample tracking script for {first_website.name}:\n"
                f"----------------------------------------\n"
                f"<script>\n"
                f"  // Track page view\n"
                f'  fetch("/track/pageview/", {{\n'
                f'    method: "POST",\n'
                f'    headers: {{"Content-Type": "application/json"}},\n'
                f"    body: JSON.stringify({{\n"
                f'      tracking_id: "{first_website.tracking_id}",\n'
                f'      session_id: "unique-session-id",\n'
                f"      page_path: window.location.pathname,\n"
                f"      page_title: document.title,\n"
                f"      referrer_url: document.referrer,\n"
                f"      // ... other data\n"
                f"    }})\n"
                f"  }});\n"
                f"</script>\n"
            )

        self.stdout.write(
            "\nYou can now:\n"
            "1. Visit the analytics dashboard\n"
            "2. Use the tracking endpoints to send data\n"
            "3. Watch real-time visitor counts update"
        )
