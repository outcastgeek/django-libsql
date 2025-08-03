"""
Enhanced data processing with embedded replica support.

This module demonstrates how embedded replicas enable:
1. Extremely high-throughput data processing
2. Local performance with cloud durability
3. Efficient batch processing with periodic sync
"""

import time
import threading
import concurrent.futures
from decimal import Decimal
from typing import List, Dict, Any
import random
import logging
from datetime import datetime

from django.db import transaction, connections, connection
from django.utils import timezone
from django.conf import settings

from .models import ProcessingJob, DataItem, ProcessingMetrics, ProcessingResult


logger = logging.getLogger(__name__)


class EmbeddedReplicaProcessor:
    """Enhanced processor leveraging embedded replica capabilities."""
    
    def __init__(self, job: ProcessingJob):
        self.job = job
        self.num_workers = (
            job.num_workers or settings.DATA_PROCESSOR_SETTINGS["MAX_WORKERS"]
        )
        self.batch_size = (
            job.batch_size or settings.DATA_PROCESSOR_SETTINGS["BATCH_SIZE"]
        )
        self.sync_threshold = settings.DATA_PROCESSOR_SETTINGS.get("SYNC_THRESHOLD", 10000)
        self.sync_after_batch = settings.DATA_PROCESSOR_SETTINGS.get("SYNC_AFTER_BATCH", True)
        
        self.stop_event = threading.Event()
        self.metrics_lock = threading.Lock()
        self.processed_count = 0
        self.failed_count = 0
        self.sync_count = 0
        self.last_sync_time = time.time()
        
    def _should_sync(self):
        """Determine if we should trigger a manual sync."""
        # Sync based on record count threshold
        if self.processed_count % self.sync_threshold == 0:
            return True
        
        # Sync if it's been too long since last sync
        if time.time() - self.last_sync_time > 30:  # 30 seconds
            return True
            
        return False
    
    def _perform_sync(self):
        """Perform manual sync and track metrics."""
        sync_start = time.time()
        try:
            connection.sync()
            sync_duration = time.time() - sync_start
            
            with self.metrics_lock:
                self.sync_count += 1
                self.last_sync_time = time.time()
            
            logger.info(
                f"✅ Manual sync #{self.sync_count} completed in {sync_duration:.3f}s "
                f"(after {self.processed_count} records)"
            )
            
            # Record sync metric
            ProcessingMetrics.objects.create(
                job=self.job,
                metric_type='sync',
                value=Decimal(f"{sync_duration:.3f}"),
                timestamp=timezone.now()
            )
            
        except Exception as e:
            logger.error(f"❌ Sync failed: {e}")
    
    def process_job(self):
        """Process job with embedded replica optimizations."""
        logger.info(
            f"🚀 Starting embedded replica job {self.job.id} "
            f"with {self.num_workers} workers"
        )
        
        # Log connection mode
        is_embedded = bool(connection.settings_dict.get('SYNC_URL'))
        mode = "Embedded Replica" if is_embedded else "Remote-Only"
        logger.info(f"   Mode: {mode}")
        logger.info(f"   Database: {connection.settings_dict['NAME']}")
        
        # Update job status
        self.job.status = "running"
        self.job.started_at = timezone.now()
        self.job.save()
        
        try:
            # Get unprocessed items
            items = list(DataItem.objects.filter(
                job=self.job, is_processed=False
            ).values_list("id", flat=True))
            
            total_items = len(items)
            self.job.total_items = total_items
            self.job.save()
            
            if total_items == 0:
                logger.warning(f"No items to process for job {self.job.id}")
                self._complete_job()
                return
            
            # Start performance monitoring
            start_time = time.time()
            
            # Process items in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                futures = []
                
                # Submit batches to workers
                for i in range(0, total_items, self.batch_size):
                    batch = items[i : i + self.batch_size]
                    future = executor.submit(self._process_batch_optimized, batch)
                    futures.append(future)
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(futures):
                    try:
                        batch_results = future.result()
                        
                        with self.metrics_lock:
                            self.processed_count += batch_results['processed']
                            self.failed_count += batch_results['failed']
                        
                        # Check if we should sync
                        if is_embedded and self._should_sync():
                            self._perform_sync()
                            
                    except Exception as e:
                        logger.error(f"Batch processing error: {e}")
                        with self.metrics_lock:
                            self.failed_count += self.batch_size
            
            # Final sync for embedded replica
            if is_embedded:
                logger.info("📤 Performing final sync...")
                self._perform_sync()
            
            # Record performance metrics
            elapsed = time.time() - start_time
            throughput = self.processed_count / elapsed if elapsed > 0 else 0
            
            ProcessingMetrics.objects.create(
                job=self.job,
                metric_type='throughput',
                value=Decimal(f"{throughput:.2f}"),
                timestamp=timezone.now()
            )
            
            logger.info(
                f"✅ Job completed: {self.processed_count} items in {elapsed:.2f}s "
                f"({throughput:.1f} items/sec)"
            )
            
            # Complete job
            self._complete_job()
            
        except Exception as e:
            logger.error(f"Job {self.job.id} failed: {e}")
            self.job.status = "failed"
            self.job.error_log = str(e)
            self.job.completed_at = timezone.now()
            self.job.save()
    
    def _process_batch_optimized(self, item_ids: List[int]) -> Dict[str, int]:
        """Process a batch with optimizations for embedded replicas."""
        processed = 0
        failed = 0
        
        # Bulk fetch items
        items = DataItem.objects.filter(id__in=item_ids)
        
        # Process in a transaction for consistency
        with transaction.atomic():
            results = []
            
            for item in items:
                try:
                    # Simulate complex processing
                    processing_time = random.uniform(0.001, 0.01)
                    time.sleep(processing_time)
                    
                    # Create result
                    result = ProcessingResult(
                        item=item,
                        result_value=Decimal(str(random.uniform(0, 100))),
                        processing_time=Decimal(f"{processing_time:.3f}"),
                        status="completed"
                    )
                    results.append(result)
                    
                    # Mark as processed
                    item.is_processed = True
                    processed += 1
                    
                except Exception as e:
                    # Record failure
                    result = ProcessingResult(
                        item=item,
                        status="failed",
                        error_message=str(e)
                    )
                    results.append(result)
                    failed += 1
            
            # Bulk create results
            ProcessingResult.objects.bulk_create(results)
            
            # Bulk update items
            DataItem.objects.bulk_update(
                [item for item in items if item.is_processed],
                ['is_processed']
            )
        
        # Optional: sync after batch if configured
        if self.sync_after_batch and hasattr(connection, 'sync'):
            try:
                connection.sync()
            except:
                pass  # Not an embedded replica
        
        return {'processed': processed, 'failed': failed}
    
    def _complete_job(self):
        """Complete the job and record final metrics."""
        self.job.status = "completed"
        self.job.completed_at = timezone.now()
        self.job.processed_items = self.processed_count
        self.job.failed_items = self.failed_count
        
        # Calculate duration
        if self.job.started_at:
            duration = (self.job.completed_at - self.job.started_at).total_seconds()
            self.job.duration_seconds = Decimal(str(duration))
        
        self.job.save()
        
        # Final sync if embedded replica
        if hasattr(connection, 'sync'):
            try:
                connection.sync()
                logger.info("✅ Final job sync completed")
            except:
                pass


def compare_processing_modes():
    """Compare performance between remote-only and embedded replica modes."""
    print("\n" + "=" * 70)
    print("🔍 Processing Mode Comparison")
    print("=" * 70)
    
    # Check current mode
    is_embedded = bool(connection.settings_dict.get('SYNC_URL'))
    current_mode = "Embedded Replica" if is_embedded else "Remote-Only"
    
    print(f"\nCurrent Mode: {current_mode}")
    print(f"Database: {connection.settings_dict['NAME']}")
    
    if is_embedded:
        print(f"Sync URL: {connection.settings_dict['SYNC_URL']}")
        print(f"Sync Interval: {connection.settings_dict.get('SYNC_INTERVAL', 'Not set')}s")
        
        print("\n✅ Benefits of Embedded Replica mode:")
        print("   - Local writes: ~1000x faster than remote")
        print("   - No network latency for reads/writes")
        print("   - Background sync doesn't block operations")
        print("   - Perfect for high-throughput batch processing")
        print("   - Resilient to network interruptions")
    else:
        print("\n💡 Consider using Embedded Replica mode for:")
        print("   - High-throughput data processing")
        print("   - Batch operations")
        print("   - Scenarios where eventual consistency is acceptable")
        print("\nTo enable, use settings_embedded.py:")
        print("   export DJANGO_SETTINGS_MODULE=settings_embedded")


# Enhanced metrics tracking
class MetricsCollector(threading.Thread):
    """Background thread to collect system metrics during processing."""
    
    def __init__(self, job: ProcessingJob, interval: float = 1.0):
        super().__init__(daemon=True)
        self.job = job
        self.interval = interval
        self.stop_event = threading.Event()
        
    def run(self):
        """Collect metrics periodically."""
        while not self.stop_event.is_set():
            try:
                # Get current stats
                processed = DataItem.objects.filter(
                    job=self.job, is_processed=True
                ).count()
                
                pending = DataItem.objects.filter(
                    job=self.job, is_processed=False
                ).count()
                
                # Record metric
                ProcessingMetrics.objects.create(
                    job=self.job,
                    metric_type='progress',
                    value=Decimal(str(processed)),
                    metadata={
                        'processed': processed,
                        'pending': pending,
                        'timestamp': datetime.now().isoformat()
                    }
                )
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
            
            self.stop_event.wait(self.interval)
    
    def stop(self):
        """Stop metrics collection."""
        self.stop_event.set()