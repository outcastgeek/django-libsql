"""Concurrent data processing engine demonstrating threading with django-libsql."""

import time
import threading
import concurrent.futures
from decimal import Decimal
from typing import List, Dict, Any
import random
import logging

from django.db import transaction, connections
from django.utils import timezone
from django.conf import settings

from .models import ProcessingJob, DataItem, ProcessingMetrics, ProcessingResult


logger = logging.getLogger(__name__)


class DataProcessor:
    """Main processor class that handles concurrent data processing."""

    def __init__(self, job: ProcessingJob):
        self.job = job
        self.num_workers = (
            job.num_workers or settings.DATA_PROCESSOR_SETTINGS["MAX_WORKERS"]
        )
        self.batch_size = (
            job.batch_size or settings.DATA_PROCESSOR_SETTINGS["BATCH_SIZE"]
        )
        self.stop_event = threading.Event()
        self.metrics_lock = threading.Lock()
        self.processed_count = 0
        self.failed_count = 0

    def process_job(self):
        """Main entry point for processing a job."""
        logger.info(f"Starting job {self.job.id} with {self.num_workers} workers")

        # Update job status
        self.job.status = "running"
        self.job.started_at = timezone.now()
        self.job.save()

        try:
            # Get unprocessed items
            items = DataItem.objects.filter(
                job=self.job, is_processed=False
            ).values_list("id", flat=True)

            total_items = len(items)
            self.job.total_items = total_items
            self.job.save()

            if total_items == 0:
                logger.warning(f"No items to process for job {self.job.id}")
                self._complete_job()
                return

            # Start metrics collector in a separate thread
            metrics_thread = threading.Thread(target=self._collect_metrics)
            metrics_thread.daemon = True
            metrics_thread.start()

            # Process items in batches using thread pool
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.num_workers
            ) as executor:
                # Submit batches to workers
                futures = []
                for i in range(0, total_items, self.batch_size):
                    batch = list(items[i : i + self.batch_size])
                    future = executor.submit(self._process_batch, batch)
                    futures.append(future)

                # Wait for all batches to complete
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Batch processing error: {e}")

            # Stop metrics collection
            self.stop_event.set()
            metrics_thread.join(timeout=5)

            # Complete job
            self._complete_job()

        except Exception as e:
            logger.error(f"Job {self.job.id} failed: {e}")
            self.job.status = "failed"
            self.job.error_log = str(e)
            self.job.completed_at = timezone.now()
            self.job.save()

    def _process_batch(self, item_ids: List[int]):
        """Process a batch of items in a single thread."""
        # Ensure each thread has its own database connection
        connections.close_all()

        logger.info(
            f"Processing batch of {len(item_ids)} items in thread {threading.current_thread().name}"
        )

        for item_id in item_ids:
            if self.stop_event.is_set():
                break

            try:
                self._process_single_item(item_id)
            except Exception as e:
                logger.error(f"Error processing item {item_id}: {e}")
                with self.metrics_lock:
                    self.failed_count += 1

    def _process_single_item(self, item_id: int):
        """Process a single data item."""
        start_time = time.time()

        # Use transaction for consistency
        with transaction.atomic():
            item = DataItem.objects.select_for_update().get(id=item_id)

            if item.is_processed:
                return

            try:
                # Simulate data processing
                processed_data = self._transform_data(item.data)

                # Update item
                item.processed_data = processed_data
                item.is_processed = True
                item.processed_at = timezone.now()
                item.processing_time = time.time() - start_time
                item.save()

                # Update counters
                with self.metrics_lock:
                    self.processed_count += 1

                # Update job progress (every 10 items to reduce DB writes)
                if self.processed_count % 10 == 0:
                    self.job.processed_items = self.processed_count
                    self.job.failed_items = self.failed_count
                    self.job.save(update_fields=["processed_items", "failed_items"])

            except Exception as e:
                item.is_failed = True
                item.error_message = str(e)
                item.save()
                raise

    def _transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw data into processed format."""
        # Simulate CPU-intensive processing
        time.sleep(random.uniform(0.01, 0.05))

        # Example transformation
        result = {
            "original_id": data.get("id"),
            "processed_at": timezone.now().isoformat(),
            "value": float(data.get("value", 0)) * 1.1,  # 10% increase
            "category": self._categorize_value(float(data.get("value", 0))),
            "quality_score": random.uniform(0.7, 1.0),
        }

        # Simulate occasional processing errors
        if random.random() < 0.05:  # 5% error rate
            raise ValueError("Simulated processing error")

        return result

    def _categorize_value(self, value: float) -> str:
        """Categorize values into ranges."""
        if value < 100:
            return "low"
        elif value < 1000:
            return "medium"
        elif value < 10000:
            return "high"
        else:
            return "very_high"

    def _collect_metrics(self):
        """Collect processing metrics periodically."""
        last_processed = 0
        last_time = time.time()

        while not self.stop_event.is_set():
            time.sleep(5)  # Collect every 5 seconds

            current_time = time.time()
            current_processed = self.processed_count

            # Calculate items per second
            time_diff = current_time - last_time
            items_diff = current_processed - last_processed
            items_per_second = items_diff / time_diff if time_diff > 0 else 0

            # Create metrics record
            ProcessingMetrics.objects.create(
                job=self.job,
                items_per_second=items_per_second,
                active_workers=self.num_workers,
                queue_size=self.job.total_items - current_processed,
            )

            last_processed = current_processed
            last_time = current_time

    def _complete_job(self):
        """Complete the job and calculate results."""
        # Final update of counts
        self.job.processed_items = self.processed_count
        self.job.failed_items = self.failed_count
        self.job.status = (
            "completed" if self.failed_count == 0 else "completed_with_errors"
        )
        self.job.completed_at = timezone.now()

        # Calculate result summary
        results = self._calculate_results()
        self.job.result_summary = results
        self.job.save()

        # Create result record
        ProcessingResult.objects.create(
            job=self.job,
            total_value=Decimal(str(results.get("total_value", 0))),
            average_value=Decimal(str(results.get("average_value", 0))),
            min_value=Decimal(str(results.get("min_value", 0))),
            max_value=Decimal(str(results.get("max_value", 0))),
            results_by_category=results.get("by_category", {}),
            total_processing_time=results.get("total_time", 0),
            average_item_time=results.get("avg_item_time", 0),
        )

        logger.info(
            f"Job {self.job.id} completed: {self.processed_count} processed, {self.failed_count} failed"
        )

    def _calculate_results(self) -> Dict[str, Any]:
        """Calculate aggregated results from processed items."""
        # Get all processed items
        processed_items = DataItem.objects.filter(
            job=self.job, is_processed=True
        ).exclude(processed_data__isnull=True)

        if not processed_items.exists():
            return {}

        # Extract values
        values = []
        categories = {}
        total_time = 0

        for item in processed_items:
            if item.processed_data:
                value = item.processed_data.get("value", 0)
                values.append(value)

                category = item.processed_data.get("category", "unknown")
                categories[category] = categories.get(category, 0) + 1

                total_time += item.processing_time or 0

        # Calculate statistics
        return {
            "total_value": sum(values),
            "average_value": sum(values) / len(values) if values else 0,
            "min_value": min(values) if values else 0,
            "max_value": max(values) if values else 0,
            "by_category": categories,
            "total_time": total_time,
            "avg_item_time": total_time / len(values) if values else 0,
        }


def process_job_async(job_id: int):
    """Process a job asynchronously in a thread."""
    try:
        job = ProcessingJob.objects.get(id=job_id)
        processor = DataProcessor(job)
        processor.process_job()
    except ProcessingJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
