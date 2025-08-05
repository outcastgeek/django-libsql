"""Create sample sensor data for the embedded replica demo."""

import random
import math
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from sensors.models import SensorReading, AggregatedData, SyncLog


class Command(BaseCommand):
    help = "Creates sample sensor data for the embedded replica demo"

    def add_arguments(self, parser):
        parser.add_argument(
            '--sensors',
            type=int,
            default=20,
            help='Number of sensors to create data for (default: 20)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days of historical data (default: 7)',
        )
        parser.add_argument(
            '--readings-per-day',
            type=int,
            default=24,
            help='Number of readings per sensor per day (default: 24)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new data',
        )

    def handle(self, *args, **options):
        self.stdout.write("Creating sample sensor data...")

        num_sensors = options['sensors']
        num_days = options['days']
        readings_per_day = options['readings_per_day']

        if options['clear']:
            self.stdout.write("Clearing existing data...")
            SensorReading.objects.all().delete()
            AggregatedData.objects.all().delete()
            SyncLog.objects.all().delete()

        # Sensor configurations
        sensor_types = [
            {"prefix": "TEMP", "location": "Factory Floor", "temp_base": 22.0, "humidity_base": 45.0},
            {"prefix": "ENV", "location": "Office", "temp_base": 21.0, "humidity_base": 40.0},
            {"prefix": "SRV", "location": "Server Room", "temp_base": 18.0, "humidity_base": 35.0},
            {"prefix": "WHR", "location": "Warehouse", "temp_base": 25.0, "humidity_base": 50.0},
            {"prefix": "LAB", "location": "Laboratory", "temp_base": 20.0, "humidity_base": 38.0},
        ]

        # Generate sensor IDs
        sensors = []
        for i in range(num_sensors):
            sensor_type = sensor_types[i % len(sensor_types)]
            sensor_id = f"{sensor_type['prefix']}-{i+1:03d}"
            sensors.append({
                "id": sensor_id,
                "location": sensor_type["location"],
                "temp_base": sensor_type["temp_base"],
                "humidity_base": sensor_type["humidity_base"]
            })

        # Create historical readings
        total_readings = 0
        readings_batch = []
        
        for day_offset in range(num_days):
            date = timezone.now().date() - timedelta(days=day_offset)
            
            for sensor in sensors:
                for reading_num in range(readings_per_day):
                    # Calculate timestamp (spread throughout the day)
                    hour_offset = (24 / readings_per_day) * reading_num
                    timestamp = timezone.make_aware(
                        timezone.datetime.combine(date, timezone.datetime.min.time()) +
                        timedelta(hours=hour_offset, minutes=random.randint(0, 30))
                    )

                    # Generate realistic sensor values with some variation
                    temp_variation = random.uniform(-3.0, 3.0)
                    humidity_variation = random.uniform(-10.0, 10.0)
                    
                    # Add daily patterns (cooler at night, warmer during day)
                    daily_temp_cycle = 2.0 * math.sin((hour_offset / 24) * 2 * 3.14159)
                    
                    temperature = Decimal(f"{sensor['temp_base'] + temp_variation + daily_temp_cycle:.2f}")
                    humidity = Decimal(f"{max(20, min(80, sensor['humidity_base'] + humidity_variation)):.2f}")

                    reading = SensorReading(
                        sensor_id=sensor["id"],
                        location=sensor["location"],
                        temperature=temperature,
                        humidity=humidity,
                        timestamp=timestamp,
                        synced=random.choice([True, False])  # Some readings not yet synced
                    )
                    
                    readings_batch.append(reading)
                    total_readings += 1

                    # Bulk create in batches for performance
                    if len(readings_batch) >= 1000:
                        SensorReading.objects.bulk_create(readings_batch)
                        readings_batch = []
                        self.stdout.write(f"  Created {total_readings} readings...")

        # Create remaining readings
        if readings_batch:
            SensorReading.objects.bulk_create(readings_batch)

        # Create aggregated data for each sensor and day
        aggregated_count = 0
        for sensor in sensors:
            for day_offset in range(num_days):
                date = timezone.now().date() - timedelta(days=day_offset)
                
                # Get readings for this sensor and date
                date_start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
                date_end = date_start + timedelta(days=1)
                daily_readings = SensorReading.objects.filter(
                    sensor_id=sensor["id"],
                    timestamp__gte=date_start,
                    timestamp__lt=date_end
                )
                
                if daily_readings.exists():
                    # Calculate aggregations
                    temps = [float(r.temperature) for r in daily_readings]
                    humidities = [float(r.humidity) for r in daily_readings]
                    
                    aggregated = AggregatedData.objects.create(
                        sensor_id=sensor["id"],
                        date=date,
                        avg_temperature=Decimal(f"{sum(temps) / len(temps):.2f}"),
                        avg_humidity=Decimal(f"{sum(humidities) / len(humidities):.2f}"),
                        min_temperature=Decimal(f"{min(temps):.2f}"),
                        max_temperature=Decimal(f"{max(temps):.2f}"),
                        reading_count=len(temps)
                    )
                    aggregated_count += 1

        # Create some sync log entries
        sync_entries = []
        for i in range(20):  # Create 20 sync log entries
            hours_ago = random.uniform(0.1, num_days * 24)
            timestamp = timezone.now() - timedelta(hours=hours_ago)
            
            sync_log = SyncLog(
                sync_type=random.choice(['manual', 'background', 'write']),
                timestamp=timestamp,
                duration_ms=random.randint(50, 2000),
                records_synced=random.randint(10, 500),
                success=random.choice([True, True, True, False]),  # 75% success rate
                error_message="" if random.random() < 0.75 else "Network timeout during sync"
            )
            sync_entries.append(sync_log)

        SyncLog.objects.bulk_create(sync_entries)

        # Perform sync if using embedded replica
        if hasattr(connection, 'sync'):
            self.stdout.write("\nSyncing embedded replica...")
            sync_start = timezone.now()
            connection.sync()
            sync_duration = (timezone.now() - sync_start).total_seconds()
            
            SyncLog.objects.create(
                sync_type='manual',
                duration_ms=int(sync_duration * 1000),
                records_synced=total_readings,
                success=True,
                error_message=""
            )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully created sample sensor data:\n"
                f"- {len(sensors)} sensors\n"
                f"- {total_readings} sensor readings\n"
                f"- {aggregated_count} aggregated daily records\n"
                f"- {len(sync_entries)} sync log entries\n"
                f"- {num_days} days of historical data"
            )
        )

        # Show sample data
        self.stdout.write("\nSample sensors:")
        for sensor in sensors[:5]:
            latest_reading = SensorReading.objects.filter(
                sensor_id=sensor["id"]
            ).order_by('-timestamp').first()
            
            if latest_reading:
                self.stdout.write(
                    f"  {sensor['id']} @ {sensor['location']}: "
                    f"T={latest_reading.temperature}°C, H={latest_reading.humidity}%"
                )

        # Show aggregation stats
        self.stdout.write("\nDaily averages (latest day):")
        latest_date = timezone.now().date()
        latest_aggregations = AggregatedData.objects.filter(date=latest_date)[:5]
        
        for agg in latest_aggregations:
            self.stdout.write(
                f"  {agg.sensor_id}: avg {agg.avg_temperature}°C "
                f"(range: {agg.min_temperature}-{agg.max_temperature}°C)"
            )

        # Show sync status
        recent_syncs = SyncLog.objects.order_by('-timestamp')[:3]
        if recent_syncs:
            self.stdout.write("\nRecent sync operations:")
            for sync in recent_syncs:
                status = "✓" if sync.success else "✗"
                self.stdout.write(
                    f"  {status} {sync.sync_type} sync: {sync.duration_ms}ms "
                    f"({sync.records_synced} records)"
                )

        self.stdout.write(
            "\nYou can now:\n"
            "1. Visit the sensors dashboard to see real-time data\n"
            "2. Run 'python manage.py simulate_sensors' for dynamic simulation\n"
            "3. Test manual sync with embedded replicas\n"
            "4. Monitor sync operations and performance"
        )