"""
Scheduler Module.

This module implements the invoice generation scheduler that runs
every 3 hours for 24 hours (8 cycles), creating batches of invoices
automatically.
"""

import signal
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from threading import Event

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config.settings import settings
from src.modules.invoices.generator import InvoiceGenerator
from src.modules.invoices.service import InvoiceService
from src.shared.utils.logger import get_logger

logger = get_logger("scheduler")

# Global scheduler instance
_scheduler: BackgroundScheduler | None = None
_shutdown_event = Event()
_start_time: datetime | None = None


def generate_invoices_job() -> None:
    """
    Job that generates and creates invoices.

    This job:
    1. Uses InvoiceGenerator to generate a batch (8-12 invoices)
    2. Creates each invoice via InvoiceService
    3. Logs execution results
    4. Handles exceptions gracefully
    """
    logger.info("Starting invoice generation job")

    try:
        # Initialize services
        generator = InvoiceGenerator()
        service = InvoiceService()

        # Generate batch of invoices
        batch_count = None  # Will generate 8-12 randomly
        invoice_data_list = generator.generate_batch(count=batch_count)

        logger.info(
            "Generated invoice batch",
            count=len(invoice_data_list),
            total_amount=sum(inv["amount"] for inv in invoice_data_list),
        )

        # Create each invoice
        created_count = 0
        failed_count = 0

        for invoice_data in invoice_data_list:
            try:
                invoice = service.create_invoice(invoice_data)
                created_count += 1
                logger.debug(
                    "Invoice created",
                    invoice_id=invoice.id,
                    stark_id=invoice.stark_invoice_id,
                    amount=invoice.amount,
                )
            except Exception as e:
                failed_count += 1
                logger.error(
                    "Failed to create invoice",
                    error=str(e),
                    customer_tax_id=invoice_data.get("customer_tax_id"),
                )

        logger.info(
            "Invoice generation job completed",
            created=created_count,
            failed=failed_count,
            total=len(invoice_data_list),
        )

    except Exception as e:
        logger.error("Invoice generation job failed", error=str(e), exc_info=True)


def _signal_handler(signum: int, _frame) -> None:
    """
    Handle shutdown signals (SIGINT, SIGTERM).

    Args:
        signum: Signal number
        _frame: Current stack frame (unused)
    """
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name}, initiating graceful shutdown...")
    _shutdown_event.set()


def _should_continue_running() -> bool:
    """
    Check if scheduler should continue running.

    Returns False if:
    - Shutdown signal received
    - 24 hours have passed since start

    Returns:
        True if should continue, False otherwise
    """
    if _shutdown_event.is_set():
        logger.info("Shutdown signal received, stopping scheduler")
        return False

    if _start_time is not None:
        elapsed = datetime.now(UTC) - _start_time
        max_duration = timedelta(hours=24)

        if elapsed >= max_duration:
            logger.info(
                "Maximum duration reached, stopping scheduler",
                elapsed_hours=elapsed.total_seconds() / 3600,
            )
            return False

    return True


def run_scheduler(
    interval_hours: int | None = None,
    max_duration_hours: int | None = None,
    run_immediately: bool = False,
) -> None:
    """
    Start the invoice generation scheduler.

    This function:
    - Configures APScheduler with IntervalTrigger
    - Schedules generate_invoices_job() every N hours (default: 3h)
    - Runs for up to 24 hours (8 cycles with 3h interval)
    - Handles graceful shutdown on SIGINT/SIGTERM
    - Can optionally run first job immediately

    Args:
        interval_hours: Hours between job executions (default: from settings)
        max_duration_hours: Maximum hours to run scheduler (default: 24)
        run_immediately: If True, runs first job immediately (default: False)
    """
    global _scheduler, _start_time

    # Get configuration
    interval_hours = interval_hours or settings.scheduler_interval_hours
    max_duration_hours = max_duration_hours or 24

    logger.info(
        "Starting scheduler",
        interval_hours=interval_hours,
        max_duration_hours=max_duration_hours,
        run_immediately=run_immediately,
    )

    # Record start time
    _start_time = datetime.now(UTC)

    # Register signal handlers for graceful shutdown (only in main thread)
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

    try:
        # Initialize scheduler
        _scheduler = BackgroundScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,  # Combine missed runs
                "max_instances": 1,  # Only one instance at a time
                "misfire_grace_time": 300,  # 5 minutes grace period
            },
        )

        # Add job with interval trigger
        _scheduler.add_job(
            func=generate_invoices_job,
            trigger=IntervalTrigger(hours=interval_hours),
            id="generate_invoices",
            name="Generate Invoices Batch",
            replace_existing=True,
        )

        # Start scheduler
        _scheduler.start()
        logger.info("Scheduler started successfully")

        # Run immediately if requested
        if run_immediately:
            logger.info("Running first job immediately")
            generate_invoices_job()

        # Keep running until shutdown signal or max duration
        while _should_continue_running():
            time.sleep(1)

        logger.info("Scheduler stopping gracefully...")

    except Exception as e:
        logger.error("Scheduler encountered an error", error=str(e), exc_info=True)
        raise

    finally:
        # Shutdown scheduler
        if _scheduler is not None and _scheduler.running:
            logger.info("Shutting down scheduler...")
            _scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown complete")


def stop_scheduler() -> None:
    """
    Stop the running scheduler gracefully.

    This function can be called to stop the scheduler programmatically
    without sending a signal.
    """
    global _scheduler

    logger.info("Stopping scheduler programmatically")
    _shutdown_event.set()

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")


def get_scheduler_status() -> dict:
    """
    Get current scheduler status.

    Returns:
        Dictionary with scheduler information:
        - running: Whether scheduler is running
        - start_time: When scheduler started (ISO format)
        - uptime_seconds: How long scheduler has been running
        - jobs: List of scheduled jobs with next run time
    """
    global _scheduler, _start_time

    status = {
        "running": _scheduler is not None and _scheduler.running,
        "start_time": _start_time.isoformat() if _start_time else None,
        "uptime_seconds": None,
        "jobs": [],
    }

    if _start_time:
        elapsed = datetime.now(UTC) - _start_time
        status["uptime_seconds"] = elapsed.total_seconds()

    if _scheduler and _scheduler.running:
        for job in _scheduler.get_jobs():
            status["jobs"].append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": (
                        job.next_run_time.isoformat() if job.next_run_time else None
                    ),
                }
            )

    return status


if __name__ == "__main__":
    """
    Entry point for running scheduler as standalone script.
    """
    logger.info("Starting scheduler from command line")
    try:
        run_scheduler(run_immediately=True)
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Scheduler failed: {e}", exc_info=True)
        sys.exit(1)
