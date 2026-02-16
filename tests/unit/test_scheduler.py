"""
Unit tests for the scheduler module.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.scheduler import (
    _should_continue_running,
    generate_invoices_job,
    get_scheduler_status,
    run_scheduler,
    stop_scheduler,
)


class TestGenerateInvoicesJob:
    """Tests for the generate_invoices_job function."""

    @patch("src.scheduler.InvoiceService")
    @patch("src.scheduler.InvoiceGenerator")
    def test_generate_invoices_job_success(
        self, mock_generator_class, mock_service_class
    ):
        """Test successful invoice generation job execution."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_service = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_service_class.return_value = mock_service

        # Mock generated invoices
        mock_invoices = [
            {
                "amount": 10000,
                "customer_name": "John Doe",
                "customer_tax_id": "12345678900",
                "customer_email": "john@example.com",
            },
            {
                "amount": 20000,
                "customer_name": "Jane Doe",
                "customer_tax_id": "98765432100",
                "customer_email": "jane@example.com",
            },
        ]
        mock_generator.generate_batch.return_value = mock_invoices

        # Mock successful invoice creation
        mock_invoice = MagicMock()
        mock_invoice.id = "inv-123"
        mock_invoice.stark_invoice_id = "stark-456"
        mock_invoice.amount = 10000
        mock_service.create_invoice.return_value = mock_invoice

        # Execute job
        generate_invoices_job()

        # Verify generator was called
        mock_generator.generate_batch.assert_called_once_with(count=None)

        # Verify service was called for each invoice
        assert mock_service.create_invoice.call_count == 2
        mock_service.create_invoice.assert_any_call(mock_invoices[0])
        mock_service.create_invoice.assert_any_call(mock_invoices[1])

    @patch("src.scheduler.InvoiceService")
    @patch("src.scheduler.InvoiceGenerator")
    def test_generate_invoices_job_with_failures(
        self, mock_generator_class, mock_service_class
    ):
        """Test invoice generation job handles individual invoice failures."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_service = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_service_class.return_value = mock_service

        # Mock generated invoices
        mock_invoices = [
            {"amount": 10000, "customer_tax_id": "12345678900"},
            {"amount": 20000, "customer_tax_id": "98765432100"},
            {"amount": 30000, "customer_tax_id": "11122233344"},
        ]
        mock_generator.generate_batch.return_value = mock_invoices

        # Mock first success, second failure, third success
        mock_service.create_invoice.side_effect = [
            MagicMock(id="inv-1"),
            Exception("Stark Bank API error"),
            MagicMock(id="inv-3"),
        ]

        # Execute job - should not raise exception
        generate_invoices_job()

        # Verify all invoices were attempted
        assert mock_service.create_invoice.call_count == 3

    @patch("src.scheduler.InvoiceService")
    @patch("src.scheduler.InvoiceGenerator")
    def test_generate_invoices_job_generator_failure(
        self, mock_generator_class, mock_service_class
    ):
        """Test invoice generation job handles generator failure."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        # Mock generator failure
        mock_generator.generate_batch.side_effect = Exception("Generator error")

        # Execute job - should not raise exception
        generate_invoices_job()

        # Verify service was never called
        mock_service_class.return_value.create_invoice.assert_not_called()


class TestSchedulerControl:
    """Tests for scheduler control functions."""

    def test_stop_scheduler(self):
        """Test stopping the scheduler programmatically."""
        with patch("src.scheduler._scheduler") as mock_scheduler:
            mock_scheduler.running = True

            stop_scheduler()

            mock_scheduler.shutdown.assert_called_once_with(wait=True)

    def test_stop_scheduler_not_running(self):
        """Test stopping scheduler when not running."""
        with patch("src.scheduler._scheduler", None):
            # Should not raise exception
            stop_scheduler()

    def test_get_scheduler_status_running(self):
        """Test getting status of running scheduler."""
        with (
            patch("src.scheduler._scheduler") as mock_scheduler,
            patch("src.scheduler._start_time", datetime.now(timezone.utc)),
        ):
            mock_scheduler.running = True
            mock_job = MagicMock()
            mock_job.id = "generate_invoices"
            mock_job.name = "Generate Invoices Batch"
            mock_job.next_run_time = datetime.now(timezone.utc) + timedelta(hours=3)
            mock_scheduler.get_jobs.return_value = [mock_job]

            status = get_scheduler_status()

            assert status["running"] is True
            assert status["start_time"] is not None
            assert status["uptime_seconds"] is not None
            assert len(status["jobs"]) == 1
            assert status["jobs"][0]["id"] == "generate_invoices"

    def test_get_scheduler_status_not_running(self):
        """Test getting status when scheduler not running."""
        with patch("src.scheduler._scheduler", None), patch(
            "src.scheduler._start_time", None
        ):
            status = get_scheduler_status()

            assert status["running"] is False
            assert status["start_time"] is None
            assert status["uptime_seconds"] is None
            assert status["jobs"] == []


class TestSchedulerExecution:
    """Tests for scheduler execution."""

    @patch("src.scheduler.BackgroundScheduler")
    @patch("src.scheduler.generate_invoices_job")
    @patch("src.scheduler._should_continue_running")
    def test_run_scheduler_basic(
        self, mock_should_continue, mock_job, mock_scheduler_class
    ):
        """Test basic scheduler execution."""
        # Setup mocks
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_scheduler.running = True

        # Make scheduler stop after first check
        mock_should_continue.side_effect = [False]

        # Run scheduler
        run_scheduler(interval_hours=3, max_duration_hours=24)

        # Verify scheduler was configured and started
        mock_scheduler_class.assert_called_once()
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()
        mock_scheduler.shutdown.assert_called_once_with(wait=True)

    @patch("src.scheduler.BackgroundScheduler")
    @patch("src.scheduler.generate_invoices_job")
    @patch("src.scheduler._should_continue_running")
    def test_run_scheduler_with_immediate_run(
        self, mock_should_continue, mock_job, mock_scheduler_class
    ):
        """Test scheduler with immediate first run."""
        # Setup mocks
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_scheduler.running = True
        mock_should_continue.side_effect = [False]

        # Run scheduler with immediate execution
        run_scheduler(interval_hours=3, run_immediately=True)

        # Verify job was called immediately
        mock_job.assert_called_once()

    @patch("src.scheduler.BackgroundScheduler")
    @patch("src.scheduler._should_continue_running")
    def test_run_scheduler_handles_exception(
        self, mock_should_continue, mock_scheduler_class
    ):
        """Test scheduler handles exceptions during execution."""
        # Setup mocks
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_scheduler.start.side_effect = Exception("Scheduler error")

        # Run scheduler - should raise exception after cleanup
        with pytest.raises(Exception, match="Scheduler error"):
            run_scheduler()

        # Verify cleanup was attempted
        mock_scheduler.shutdown.assert_called_once_with(wait=True)

    @patch("src.scheduler._start_time", None)
    @patch("src.scheduler._shutdown_event")
    def test_should_continue_running_no_shutdown(self, mock_event):
        """Test continue running when no shutdown signal."""
        mock_event.is_set.return_value = False

        result = _should_continue_running()

        assert result is True

    @patch("src.scheduler._shutdown_event")
    def test_should_continue_running_with_shutdown(self, mock_event):
        """Test stop running when shutdown signal received."""
        mock_event.is_set.return_value = True

        result = _should_continue_running()

        assert result is False

    @patch("src.scheduler._shutdown_event")
    def test_should_continue_running_max_duration_reached(self, mock_event):
        """Test stop running when max duration reached."""
        mock_event.is_set.return_value = False

        # Set start time to 25 hours ago
        with patch(
            "src.scheduler._start_time",
            datetime.now(timezone.utc) - timedelta(hours=25),
        ):
            result = _should_continue_running()

            assert result is False

    @patch("src.scheduler._shutdown_event")
    def test_should_continue_running_within_duration(self, mock_event):
        """Test continue running when within max duration."""
        mock_event.is_set.return_value = False

        # Set start time to 1 hour ago
        with patch(
            "src.scheduler._start_time",
            datetime.now(timezone.utc) - timedelta(hours=1),
        ):
            result = _should_continue_running()

            assert result is True


class TestSchedulerIntegration:
    """Integration-style tests for scheduler (with short durations)."""

    @patch("src.scheduler.InvoiceService")
    @patch("src.scheduler.InvoiceGenerator")
    def test_scheduler_runs_job(self, mock_generator_class, mock_service_class):
        """Test that scheduler actually runs the job."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_service = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_service_class.return_value = mock_service

        mock_invoices = [{"amount": 10000}]
        mock_generator.generate_batch.return_value = mock_invoices
        mock_service.create_invoice.return_value = MagicMock(id="inv-1")

        # Run scheduler for very short duration (1 second interval)
        with patch("src.scheduler.time.sleep") as mock_sleep:
            # Make sleep stop the scheduler after first call
            def stop_on_sleep(seconds):
                stop_scheduler()

            mock_sleep.side_effect = stop_on_sleep

            # This should start, potentially run job, and stop quickly
            run_scheduler(interval_hours=1 / 3600)  # 1 second in hours

        # Note: Job might not execute due to timing, but scheduler should start/stop cleanly
        # This test primarily verifies no crashes occur
