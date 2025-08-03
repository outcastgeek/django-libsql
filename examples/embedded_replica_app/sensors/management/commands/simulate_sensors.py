"""
Management command to simulate sensor data in ALL modes:
1. Regular Python (single-threaded)
2. With threads
3. With threads + no-GIL
4. With threads + no-GIL + Django ORM

This command automatically detects the execution mode and adapts.
"""

import os
import sys
import time
import random
import threading
import concurrent.futures
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from sensors.models import SensorReading, AggregatedData, SyncLog


class Command(BaseCommand):
    help = 'Simulate IoT sensor data generation in various modes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sensors',
            type=int,
            default=10,
            help='Number of sensors to simulate'
        )
        parser.add_argument(
            '--duration',
            type=int,
            default=30,
            help='Duration to run simulation (seconds)'
        )
        parser.add_argument(
            '--threads',
            type=int,
            default=0,
            help='Number of threads (0 = auto-detect based on mode)'
        )
        parser.add_argument(
            '--mode',
            choices=['single', 'multi', 'auto'],
            default='auto',
            help='Execution mode'
        )

    def handle(self, *args, **options):
        num_sensors = options['sensors']
        duration = options['duration']
        num_threads = options['threads']
        mode = options['mode']

        # Detect execution environment
        gil_status = self.get_gil_status()
        is_embedded = hasattr(connection, 'sync')
        
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(f"SENSOR SIMULATION - DJANGO MANAGEMENT COMMAND")
        self.stdout.write(f"{'='*70}")
        self.stdout.write(f"Python: {sys.version}")
        self.stdout.write(f"GIL Status: {gil_status}")
        self.stdout.write(f"Database: {'Embedded Replica' if is_embedded else 'Remote Only'}")
        self.stdout.write(f"{'='*70}\n")

        # Auto-detect mode
        if mode == 'auto':
            if 'NO-GIL' in gil_status and num_threads == 0:
                num_threads = 8  # Use more threads with no-GIL
                mode = 'multi'
            elif num_threads > 0:
                mode = 'multi'
            else:
                mode = 'single'

        self.stdout.write(f"Mode: {mode.upper()}")
        self.stdout.write(f"Sensors: {num_sensors}")
        self.stdout.write(f"Duration: {duration}s")
        if mode == 'multi':
            self.stdout.write(f"Threads: {num_threads}")

        # Clear existing data
        self.stdout.write("\nClearing existing data...")
        SensorReading.objects.all().delete()
        AggregatedData.objects.all().delete()
        SyncLog.objects.all().delete()

        # Run simulation
        start_time = time.time()
        
        if mode == 'single':
            records = self.run_single_threaded(num_sensors, duration)
        else:
            records = self.run_multi_threaded(num_sensors, duration, num_threads)

        elapsed = time.time() - start_time

        # Final sync for embedded replicas
        if is_embedded:
            self.stdout.write("\nPerforming final sync...")
            sync_start = time.time()
            connection.sync()
            sync_duration = time.time() - sync_start
            
            SyncLog.objects.create(
                sync_type='final',
                records_synced=records,
                duration_ms=int(sync_duration * 1000),
                success=True,
                details={'command': 'simulate_sensors'}
            )

        # Report results
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS("SIMULATION COMPLETE"))
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Total records: {records}")
        self.stdout.write(f"Duration: {elapsed:.2f}s")
        self.stdout.write(f"Throughput: {records/elapsed:.2f} records/sec")
        
        if is_embedded:
            self.stdout.write(f"Final sync time: {sync_duration:.3f}s")

        # Show sample data
        self.show_sample_data()

    def run_single_threaded(self, num_sensors, duration):
        """Run simulation in single-threaded mode."""
        self.stdout.write("\nRunning single-threaded simulation...")
        
        sensors = [f"SENSOR-{i:03d}" for i in range(num_sensors)]
        locations = ["Factory Floor", "Warehouse", "Office", "Server Room", "Lab"]
        
        start_time = time.time()
        record_count = 0
        
        while time.time() - start_time < duration:
            # Generate batch of readings
            batch = []
            for sensor in sensors:
                reading = SensorReading(
                    sensor_id=sensor,
                    location=random.choice(locations),
                    temperature=Decimal(f"{20 + random.random() * 10:.2f}"),
                    humidity=Decimal(f"{40 + random.random() * 20:.2f}"),
                    pressure=Decimal(f"{1000 + random.random() * 50:.2f}"),
                    timestamp=timezone.now()
                )
                batch.append(reading)
            
            # Bulk create
            SensorReading.objects.bulk_create(batch)
            record_count += len(batch)
            
            # Sync periodically for embedded replicas
            if hasattr(connection, 'sync') and record_count % 100 == 0:
                connection.sync()
            
            # Show progress
            if record_count % 100 == 0:
                self.stdout.write(f"  Generated {record_count} readings...")
            
            time.sleep(0.1)  # Small delay
        
        return record_count

    def run_multi_threaded(self, num_sensors, duration, num_threads):
        """Run simulation in multi-threaded mode."""
        self.stdout.write(f"\nRunning multi-threaded simulation ({num_threads} threads)...")
        
        sensors = [f"SENSOR-{i:03d}" for i in range(num_sensors)]
        locations = ["Factory Floor", "Warehouse", "Office", "Server Room", "Lab"]
        
        # Divide sensors among threads
        sensors_per_thread = len(sensors) // num_threads
        sensor_groups = []
        for i in range(num_threads):
            start_idx = i * sensors_per_thread
            end_idx = start_idx + sensors_per_thread if i < num_threads - 1 else len(sensors)
            sensor_groups.append(sensors[start_idx:end_idx])
        
        # Shared state
        stop_event = threading.Event()
        record_counts = [0] * num_threads
        lock = threading.Lock()
        
        def worker(thread_id, sensor_list):
            """Worker thread function."""
            local_count = 0
            
            while not stop_event.is_set():
                # Generate readings for assigned sensors
                batch = []
                for sensor in sensor_list:
                    reading = SensorReading(
                        sensor_id=sensor,
                        location=random.choice(locations),
                        temperature=Decimal(f"{20 + random.random() * 10:.2f}"),
                        humidity=Decimal(f"{40 + random.random() * 20:.2f}"),
                        pressure=Decimal(f"{1000 + random.random() * 50:.2f}"),
                        timestamp=timezone.now()
                    )
                    batch.append(reading)
                
                # Bulk create with thread-safe transaction
                with transaction.atomic():
                    SensorReading.objects.bulk_create(batch)
                    local_count += len(batch)
                
                # Update shared count
                with lock:
                    record_counts[thread_id] = local_count
                
                # Sync periodically for embedded replicas
                if hasattr(connection, 'sync') and local_count % 50 == 0:
                    connection.sync()
                
                time.sleep(0.05)  # Small delay
        
        # Start threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Submit workers
            futures = []
            for i, sensor_group in enumerate(sensor_groups):
                future = executor.submit(worker, i, sensor_group)
                futures.append(future)
            
            # Run for duration
            time.sleep(duration)
            stop_event.set()
            
            # Wait for completion
            concurrent.futures.wait(futures)
        
        total_records = sum(record_counts)
        self.stdout.write(f"  Total records from all threads: {total_records}")
        
        return total_records

    def show_sample_data(self):
        """Show sample of generated data."""
        self.stdout.write("\nSample readings:")
        
        # Recent readings
        recent = SensorReading.objects.order_by('-timestamp')[:5]
        for reading in recent:
            self.stdout.write(
                f"  {reading.sensor_id} @ {reading.location}: "
                f"T={reading.temperature}°C, H={reading.humidity}%, P={reading.pressure}hPa"
            )
        
        # Stats by sensor
        self.stdout.write("\nReadings per sensor:")
        stats = SensorReading.objects.values('sensor_id').annotate(
            count=models.Count('id')
        ).order_by('-count')[:5]
        
        for stat in stats:
            self.stdout.write(f"  {stat['sensor_id']}: {stat['count']} readings")

    def get_gil_status(self):
        """Check if Python is running with GIL disabled."""
        gil_disabled = sys._is_gil_enabled() == False if hasattr(sys, '_is_gil_enabled') else False
        return "NO-GIL (Free-Threading)" if gil_disabled else "WITH GIL"


# Missing import
from django.db import models