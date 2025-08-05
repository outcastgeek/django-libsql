"""Create sample benchmark results for the benchmark app."""

import sys
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from benchmark_app.models import BenchmarkResult, TestRecord


class Command(BaseCommand):
    help = "Creates sample benchmark results and test records for the benchmark app"

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new data',
        )

    def handle(self, *args, **options):
        self.stdout.write("Creating sample benchmark data...")

        if options['clear']:
            self.stdout.write("Clearing existing data...")
            BenchmarkResult.objects.all().delete()
            TestRecord.objects.all().delete()

        # Get Python version info
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # Create historical benchmark results
        test_scenarios = [
            {
                "name": "Django ORM CRUD",
                "modes": [
                    {"mode": "gil-single", "gil_enabled": True, "threads": 1, "base_throughput": 0.9},
                    {"mode": "gil-multi", "gil_enabled": True, "threads": 4, "base_throughput": 1.2},
                    {"mode": "nogil-single", "gil_enabled": False, "threads": 1, "base_throughput": 1.0},
                    {"mode": "nogil-multi", "gil_enabled": False, "threads": 4, "base_throughput": 2.1},
                    {"mode": "nogil-multi-8", "gil_enabled": False, "threads": 8, "base_throughput": 3.2},
                ]
            },
            {
                "name": "Raw SQL Operations",
                "modes": [
                    {"mode": "gil-single", "gil_enabled": True, "threads": 1, "base_throughput": 3.1},
                    {"mode": "gil-multi", "gil_enabled": True, "threads": 4, "base_throughput": 4.5},
                    {"mode": "nogil-single", "gil_enabled": False, "threads": 1, "base_throughput": 3.3},
                    {"mode": "nogil-multi", "gil_enabled": False, "threads": 4, "base_throughput": 16.7},
                    {"mode": "nogil-multi-8", "gil_enabled": False, "threads": 8, "base_throughput": 28.4},
                ]
            },
            {
                "name": "Database Connection Test",
                "modes": [
                    {"mode": "local", "gil_enabled": True, "threads": 1, "base_throughput": 1200.0},
                    {"mode": "embedded", "gil_enabled": True, "threads": 1, "base_throughput": 800.0},
                    {"mode": "remote", "gil_enabled": True, "threads": 1, "base_throughput": 120.0},
                ]
            },
            {
                "name": "Bulk Insert Performance",
                "modes": [
                    {"mode": "local-batch", "gil_enabled": True, "threads": 1, "base_throughput": 5000.0},
                    {"mode": "embedded-batch", "gil_enabled": True, "threads": 1, "base_throughput": 3500.0},
                    {"mode": "remote-batch", "gil_enabled": True, "threads": 1, "base_throughput": 800.0},
                ]
            }
        ]

        created_results = 0
        
        # Generate results for last 30 days
        for days_ago in range(30):
            result_date = timezone.now() - timedelta(days=days_ago)
            
            for scenario in test_scenarios:
                for mode_config in scenario["modes"]:
                    # Add some variation to the results
                    variation = random.uniform(0.8, 1.2)
                    throughput = mode_config["base_throughput"] * variation
                    
                    # Calculate operations and duration
                    duration = random.uniform(10.0, 60.0)  # 10-60 seconds
                    operations = int(throughput * duration)
                    
                    # Determine if it's embedded replica
                    is_embedded = "embedded" in mode_config["mode"] or mode_config["mode"] in ["nogil-multi", "nogil-multi-8"]
                    
                    result = BenchmarkResult.objects.create(
                        test_name=scenario["name"],
                        mode=mode_config["mode"],
                        threads=mode_config["threads"],
                        operations=operations,
                        duration=duration,
                        throughput=throughput,
                        python_version=python_version,
                        gil_enabled=mode_config["gil_enabled"],
                        is_embedded=is_embedded,
                        timestamp=result_date
                    )
                    
                    created_results += 1
                    
                    # Only show progress for recent results
                    if days_ago < 3:
                        self.stdout.write(f"Created: {result}")

        # Create some test records for actual benchmarking
        test_data_templates = [
            {"name": "user_record", "base_value": 100},
            {"name": "product_item", "base_value": 250},
            {"name": "order_entry", "base_value": 500},
            {"name": "analytics_event", "base_value": 1000},
            {"name": "sensor_reading", "base_value": 50},
        ]

        created_records = 0
        for i in range(500):  # Create 500 test records
            template = random.choice(test_data_templates)
            
            record = TestRecord.objects.create(
                name=f"{template['name']}_{i:03d}",
                value=template["base_value"] + random.randint(-50, 50),
                data=f"Test data for {template['name']} record {i}. " * random.randint(1, 5)
            )
            created_records += 1

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully created sample benchmark data:\n"
                f"- {created_results} benchmark results\n"
                f"- {created_records} test records\n"
                f"- Data spans last 30 days"
            )
        )

        # Show some statistics
        latest_results = BenchmarkResult.objects.order_by('-timestamp')[:5]
        self.stdout.write("\nLatest benchmark results:")
        for result in latest_results:
            self.stdout.write(f"  {result}")

        # Show performance comparison
        self.stdout.write("\nPerformance summary (latest results by test):")
        for scenario in test_scenarios:
            latest = BenchmarkResult.objects.filter(
                test_name=scenario["name"]
            ).order_by('-timestamp').first()
            
            if latest:
                self.stdout.write(f"  {scenario['name']}: {latest.throughput:.2f} ops/sec ({latest.mode})")

        self.stdout.write(
            "\nYou can now:\n"
            "1. Visit the benchmark dashboard to see results\n"
            "2. Run 'python manage.py run_benchmark' to add new results\n"
            "3. Compare different execution modes and configurations"
        )