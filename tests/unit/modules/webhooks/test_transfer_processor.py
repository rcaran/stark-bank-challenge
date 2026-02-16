"""Unit tests for TransferWebhookProcessor."""

from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

import pytest

from src.modules.webhooks.events import (
    TRANSFER_COMPLETED,
    TRANSFER_FAILED,
    TRANSFER_PROCESSING,
)
from src.modules.webhooks.transfer_processor import TransferWebhookProcessor
from src.modules.webhooks.models import TransferWebhookPayload
from src.shared.utils.errors import NotFoundError


class MockTransfer:
    """Mock transfer model for testing."""

    def __init__(
        self,
        id: str = "transfer-123",
        stark_transfer_id: str = "stark-transfer-456",
        invoice_id: str = "inv-789",
        amount: float = 100.00,
        status: str = "created",
        external_id: str = "invoice-inv-789",
        created_at: datetime = None,
        updated_at: datetime = None,
        completed_at: datetime = None,
        error_message: str = None,
        error_code: str = None,
        fee: float = None,
    ):
        self.id = id
        self.stark_transfer_id = stark_transfer_id
        self.invoice_id = invoice_id
        self.amount = amount
        self.status = status
        self.external_id = external_id
        self.created_at = created_at or datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
        self.updated_at = updated_at
        self.completed_at = completed_at
        self.error_message = error_message
        self.error_code = error_code
        self.fee = fee


class TestTransferWebhookProcessor:
    """Tests for TransferWebhookProcessor class."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock transfer repository."""
        return Mock()

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return Mock()

    @pytest.fixture
    def processor(self, mock_repository, mock_event_bus):
        """Create processor with mocked dependencies."""
        return TransferWebhookProcessor(
            transfer_repository=mock_repository,
            event_bus=mock_event_bus,
        )

    @pytest.fixture
    def sample_transfer(self):
        """Create sample transfer model."""
        return MockTransfer(
            id="transfer-123",
            stark_transfer_id="stark-transfer-456",
            invoice_id="inv-789",
            amount=99.50,
            status="created",
            external_id="invoice-inv-789",
        )

    @pytest.fixture
    def success_webhook_payload(self):
        """Create sample successful transfer webhook payload."""
        return TransferWebhookPayload(
            transfer_id="stark-transfer-456",
            status="success",
            amount=9950,  # 99.50 in centavos
            external_id="invoice-inv-789",
            bank_code="20018183",
            branch_code="0001",
            account_number="6341320293482496",
            account_type="payment",
            name="Stark Bank S.A.",
            tax_id="20.018.183/0001-80",
            fee=0,
            created=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
            updated=datetime(2026, 2, 16, 14, 30, 0, tzinfo=timezone.utc),
        )

    @pytest.fixture
    def failed_webhook_payload(self):
        """Create sample failed transfer webhook payload."""
        return TransferWebhookPayload(
            transfer_id="stark-transfer-456",
            status="failed",
            amount=9950,
            external_id="invoice-inv-789",
            bank_code="20018183",
            branch_code="0001",
            account_number="6341320293482496",
            name="Stark Bank S.A.",
            tax_id="20.018.183/0001-80",
            error_code="invalidAccountNumber",
            error_message="Invalid account number",
            created=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
            updated=datetime(2026, 2, 16, 14, 30, 0, tzinfo=timezone.utc),
        )

    @pytest.fixture
    def processing_webhook_payload(self):
        """Create sample processing transfer webhook payload."""
        return TransferWebhookPayload(
            transfer_id="stark-transfer-456",
            status="processing",
            amount=9950,
            external_id="invoice-inv-789",
            bank_code="20018183",
            branch_code="0001",
            account_number="6341320293482496",
            name="Stark Bank S.A.",
            tax_id="20.018.183/0001-80",
            created=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
            updated=datetime(2026, 2, 16, 14, 0, 0, tzinfo=timezone.utc),
        )

    # ==========================================================================
    # process() tests - Status "success"
    # ==========================================================================

    def test_process_successful_transfer(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
        success_webhook_payload,
    ):
        """Test successful processing of transfer completion webhook."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        processor.process(success_webhook_payload)

        # Verify repository was called to find transfer
        mock_repository.get_by_stark_id.assert_called_once_with("stark-transfer-456")

        # Verify transfer was updated
        mock_repository.update.assert_called_once()
        updated_transfer = mock_repository.update.call_args[0][0]
        assert updated_transfer.status == "success"
        assert updated_transfer.completed_at is not None
        assert updated_transfer.updated_at is not None

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.event_type == TRANSFER_COMPLETED
        assert event.payload["transfer_id"] == "transfer-123"
        assert event.payload["stark_transfer_id"] == "stark-transfer-456"
        assert event.payload["invoice_id"] == "inv-789"
        assert event.payload["amount"] == 99.50

    def test_process_success_sets_completed_at_from_webhook(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
        success_webhook_payload,
    ):
        """Test that completed_at timestamp is set from webhook updated field."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        processor.process(success_webhook_payload)

        updated_transfer = mock_repository.update.call_args[0][0]
        assert updated_transfer.completed_at == datetime(
            2026, 2, 16, 14, 30, 0, tzinfo=timezone.utc
        )

    def test_process_success_sets_fee_if_available(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
    ):
        """Test that fee is set when available in webhook."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        payload = TransferWebhookPayload(
            transfer_id="stark-transfer-456",
            status="success",
            amount=9950,
            fee=100,  # 1.00 real
            external_id="invoice-inv-789",
        )

        processor.process(payload)

        updated_transfer = mock_repository.update.call_args[0][0]
        assert updated_transfer.fee == 1.00

    # ==========================================================================
    # process() tests - Status "failed"
    # ==========================================================================

    def test_process_failed_transfer(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
        failed_webhook_payload,
    ):
        """Test processing of failed transfer webhook."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        processor.process(failed_webhook_payload)

        # Verify repository was called
        mock_repository.get_by_stark_id.assert_called_once_with("stark-transfer-456")

        # Verify transfer was updated
        mock_repository.update.assert_called_once()
        updated_transfer = mock_repository.update.call_args[0][0]
        assert updated_transfer.status == "failed"
        assert updated_transfer.error_message == "Invalid account number"
        assert updated_transfer.error_code == "invalidAccountNumber"
        assert updated_transfer.updated_at is not None

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.event_type == TRANSFER_FAILED
        assert event.payload["transfer_id"] == "transfer-123"
        assert event.payload["error_message"] == "Invalid account number"
        assert event.payload["error_code"] == "invalidAccountNumber"

    def test_process_failed_stores_error_info(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
    ):
        """Test that error information is properly stored."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        payload = TransferWebhookPayload(
            transfer_id="stark-transfer-456",
            status="failed",
            amount=9950,
            external_id="invoice-inv-789",
            error_code="insufficientFunds",
            error_message="Insufficient funds in source account",
        )

        processor.process(payload)

        updated_transfer = mock_repository.update.call_args[0][0]
        assert updated_transfer.error_message == "Insufficient funds in source account"
        assert updated_transfer.error_code == "insufficientFunds"

    # ==========================================================================
    # process() tests - Status "processing"
    # ==========================================================================

    def test_process_processing_transfer(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
        processing_webhook_payload,
    ):
        """Test processing of transfer in processing state."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        processor.process(processing_webhook_payload)

        # Verify repository was called
        mock_repository.get_by_stark_id.assert_called_once_with("stark-transfer-456")

        # Verify transfer was updated
        mock_repository.update.assert_called_once()
        updated_transfer = mock_repository.update.call_args[0][0]
        assert updated_transfer.status == "processing"
        assert updated_transfer.updated_at is not None

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.event_type == TRANSFER_PROCESSING
        assert event.payload["transfer_id"] == "transfer-123"
        assert event.payload["stark_transfer_id"] == "stark-transfer-456"

    # ==========================================================================
    # process() tests - Error handling
    # ==========================================================================

    def test_process_transfer_not_found_raises_error(
        self,
        processor,
        mock_repository,
        success_webhook_payload,
    ):
        """Test that NotFoundError is raised when transfer not found."""
        mock_repository.get_by_stark_id.return_value = None

        with pytest.raises(NotFoundError, match="Transfer not found"):
            processor.process(success_webhook_payload)

    def test_process_unknown_status_does_nothing(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
    ):
        """Test that unknown status is handled gracefully."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        payload = TransferWebhookPayload(
            transfer_id="stark-transfer-456",
            status="unknown_status",
            amount=9950,
            external_id="invoice-inv-789",
        )

        processor.process(payload)

        # Repository should be queried but not updated
        mock_repository.get_by_stark_id.assert_called_once()
        mock_repository.update.assert_not_called()
        mock_event_bus.publish.assert_not_called()

    # ==========================================================================
    # Event metadata tests
    # ==========================================================================

    def test_completed_event_metadata_contains_source(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
        success_webhook_payload,
    ):
        """Test that completed event metadata contains webhook source info."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        processor.process(success_webhook_payload)

        event = mock_event_bus.publish.call_args[0][0]
        assert event.metadata["source"] == "webhook"
        assert event.metadata["webhook_transfer_id"] == "stark-transfer-456"

    def test_failed_event_metadata_contains_error_code(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
        failed_webhook_payload,
    ):
        """Test that failed event metadata contains error info."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        processor.process(failed_webhook_payload)

        event = mock_event_bus.publish.call_args[0][0]
        assert event.metadata["source"] == "webhook"
        assert event.metadata["error_code"] == "invalidAccountNumber"

    def test_processing_event_metadata_contains_source(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
        processing_webhook_payload,
    ):
        """Test that processing event metadata contains webhook source info."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        processor.process(processing_webhook_payload)

        event = mock_event_bus.publish.call_args[0][0]
        assert event.metadata["source"] == "webhook"
        assert event.metadata["webhook_transfer_id"] == "stark-transfer-456"

    # ==========================================================================
    # Edge cases
    # ==========================================================================

    def test_process_success_uses_current_time_when_updated_missing(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
    ):
        """Test that current time is used when webhook has no updated field."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        payload = TransferWebhookPayload(
            transfer_id="stark-transfer-456",
            status="success",
            amount=9950,
            external_id="invoice-inv-789",
            updated=None,  # No updated timestamp
        )

        processor.process(payload)

        updated_transfer = mock_repository.update.call_args[0][0]
        assert updated_transfer.completed_at is not None
        # Should be close to now
        time_diff = abs(
            (datetime.now(timezone.utc) - updated_transfer.completed_at).total_seconds()
        )
        assert time_diff < 5  # Within 5 seconds

    def test_process_handles_transfer_without_invoice_id(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        success_webhook_payload,
    ):
        """Test processing when transfer has no associated invoice."""
        transfer_without_invoice = MockTransfer(
            id="transfer-123",
            stark_transfer_id="stark-transfer-456",
            amount=99.50,
            status="created",
            external_id="manual-transfer",
        )
        # Remove invoice_id attribute
        delattr(transfer_without_invoice, 'invoice_id')

        mock_repository.get_by_stark_id.return_value = transfer_without_invoice

        processor.process(success_webhook_payload)

        # Event should be published with invoice_id as None
        event = mock_event_bus.publish.call_args[0][0]
        assert event.payload["invoice_id"] is None

    def test_process_handles_null_external_id(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
    ):
        """Test processing when external_id is None."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        payload = TransferWebhookPayload(
            transfer_id="stark-transfer-456",
            status="success",
            amount=9950,
            external_id=None,  # No external_id
        )

        processor.process(payload)

        event = mock_event_bus.publish.call_args[0][0]
        assert event.payload["external_id"] == ""

    def test_process_handles_null_error_fields(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
    ):
        """Test processing failed transfer with null error fields."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        payload = TransferWebhookPayload(
            transfer_id="stark-transfer-456",
            status="failed",
            amount=9950,
            external_id="invoice-inv-789",
            error_code=None,
            error_message=None,
        )

        processor.process(payload)

        event = mock_event_bus.publish.call_args[0][0]
        assert event.payload["error_code"] is None
        assert event.payload["error_message"] is None

    def test_process_updates_only_relevant_fields(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
        success_webhook_payload,
    ):
        """Test that only status-related fields are updated."""
        original_amount = sample_transfer.amount
        original_external_id = sample_transfer.external_id
        original_created_at = sample_transfer.created_at

        mock_repository.get_by_stark_id.return_value = sample_transfer

        processor.process(success_webhook_payload)

        updated_transfer = mock_repository.update.call_args[0][0]

        # These fields should NOT change
        assert updated_transfer.amount == original_amount
        assert updated_transfer.external_id == original_external_id
        assert updated_transfer.created_at == original_created_at

        # These fields SHOULD change
        assert updated_transfer.status == "success"
        assert updated_transfer.updated_at is not None
        assert updated_transfer.completed_at is not None

    def test_process_multiple_webhooks_same_transfer(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_transfer,
        processing_webhook_payload,
        success_webhook_payload,
    ):
        """Test processing multiple webhooks for same transfer (processing then success)."""
        mock_repository.get_by_stark_id.return_value = sample_transfer

        # First webhook: processing
        processor.process(processing_webhook_payload)

        assert mock_repository.update.call_count == 1
        first_update = mock_repository.update.call_args[0][0]
        assert first_update.status == "processing"

        # Reset mock for second call
        mock_repository.reset_mock()
        mock_event_bus.reset_mock()

        # Update sample_transfer status for second call
        sample_transfer.status = "processing"
        mock_repository.get_by_stark_id.return_value = sample_transfer

        # Second webhook: success
        processor.process(success_webhook_payload)

        assert mock_repository.update.call_count == 1
        second_update = mock_repository.update.call_args[0][0]
        assert second_update.status == "success"
        assert second_update.completed_at is not None
