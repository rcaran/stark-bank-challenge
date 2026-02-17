"""Unit tests for TransferService."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.modules.transfers.events import TRANSFER_FAILED, TRANSFER_INITIATED
from src.modules.transfers.models import TransferModel, TransferStatus
from src.modules.transfers.service import TransferService
from src.shared.utils.errors import NotFoundError, RetriableError, ValidationError


class TestTransferService:
    """Tests for TransferService."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        return Mock()

    @pytest.fixture
    def mock_stark_api(self):
        """Create mock Stark Bank Transfer API."""
        mock = Mock()
        # Default successful response
        mock.create_transfer.return_value = Mock(
            id="stark-transfer-123",
            amount=9500,  # in cents
            status="created",
            external_id="invoice-test-invoice-id",
        )
        return mock

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return Mock()

    @pytest.fixture
    def service(self, mock_repository, mock_stark_api, mock_event_bus):
        """Create service with mocked dependencies."""
        return TransferService(
            repository=mock_repository,
            stark_api=mock_stark_api,
            event_bus=mock_event_bus,
        )

    @pytest.fixture
    def paid_invoice(self):
        """Create a paid invoice with net amount."""
        return InvoiceModel(
            id="test-invoice-id",
            amount=100.0,
            customer_name="João Silva",
            customer_tax_id="529.982.247-25",
            customer_email="joao@example.com",
            status=InvoiceStatus.PAID,
            stark_invoice_id="stark-invoice-123",
            paid_at=datetime.now(UTC),
            fee=5.0,
            net_amount=95.0,
        )

    def test_create_transfer_success(
        self,
        service,
        mock_repository,
        mock_stark_api,
        mock_event_bus,
        paid_invoice,
    ):
        """Test successful transfer creation."""
        # Setup: no existing transfer
        mock_repository.get_by_external_id.return_value = None

        # Execute
        result = service.create_transfer(paid_invoice)

        # Verify Stark API was called with correct parameters
        mock_stark_api.create_transfer.assert_called_once()
        call_kwargs = mock_stark_api.create_transfer.call_args[1]
        assert call_kwargs["amount"] == 9500  # 95.0 * 100 (cents)
        assert call_kwargs["external_id"] == "invoice-test-invoice-id"
        assert call_kwargs["name"] == "Stark Bank S.A."
        assert call_kwargs["tax_id"] == "20018183000180"
        assert call_kwargs["bank_code"] == "20018183"
        assert call_kwargs["branch_code"] == "0001"
        assert call_kwargs["account_number"] == "6341320293482496"
        assert call_kwargs["account_type"] == "payment"
        assert "invoice-payment" in call_kwargs["tags"]

        # Verify transfer was persisted
        mock_repository.create.assert_called_once()
        created_transfer = mock_repository.create.call_args[0][0]
        assert created_transfer.invoice_id == paid_invoice.id
        assert created_transfer.amount == 95.0
        assert created_transfer.external_id == "invoice-test-invoice-id"
        assert created_transfer.status == TransferStatus.CREATED
        assert created_transfer.stark_transfer_id == "stark-transfer-123"

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert published_event.event_type == TRANSFER_INITIATED
        payload = published_event.payload
        assert payload["invoice_id"] == paid_invoice.id
        assert payload["stark_transfer_id"] == "stark-transfer-123"

        # Verify return value
        assert result.invoice_id == paid_invoice.id
        assert result.amount == 95.0
        assert result.status == TransferStatus.CREATED

    def test_create_transfer_idempotency(
        self,
        service,
        mock_repository,
        mock_stark_api,
        mock_event_bus,
        paid_invoice,
    ):
        """Test that creating transfer for same invoice returns existing transfer."""
        # Setup: transfer already exists
        existing_transfer = TransferModel(
            id="existing-transfer-id",
            invoice_id=paid_invoice.id,
            amount=95.0,
            external_id="invoice-test-invoice-id",
            stark_transfer_id="stark-transfer-123",
            status=TransferStatus.CREATED,
        )
        mock_repository.get_by_external_id.return_value = existing_transfer

        # Execute
        result = service.create_transfer(paid_invoice)

        # Verify Stark API was NOT called
        mock_stark_api.create_transfer.assert_not_called()

        # Verify no new transfer was created
        mock_repository.create.assert_not_called()

        # Verify no event was published
        mock_event_bus.publish.assert_not_called()

        # Verify existing transfer was returned
        assert result == existing_transfer

    def test_create_transfer_invalid_net_amount(self, service, paid_invoice):
        """Test transfer creation with invalid net amount."""
        # Setup: invoice with zero net amount
        paid_invoice.net_amount = 0

        # Execute and verify
        with pytest.raises(ValidationError) as exc_info:
            service.create_transfer(paid_invoice)

        assert "Invalid net_amount" in str(exc_info.value)

    def test_create_transfer_negative_net_amount(self, service, paid_invoice):
        """Test transfer creation with negative net amount."""
        # Setup: invoice with negative net amount
        paid_invoice.net_amount = -10.0

        # Execute and verify
        with pytest.raises(ValidationError) as exc_info:
            service.create_transfer(paid_invoice)

        assert "Invalid net_amount" in str(exc_info.value)

    def test_create_transfer_retriable_error(
        self,
        service,
        mock_repository,
        mock_stark_api,
        mock_event_bus,
        paid_invoice,
    ):
        """Test transfer creation with retriable error."""
        # Setup: no existing transfer, but API fails with retriable error
        mock_repository.get_by_external_id.return_value = None
        mock_stark_api.create_transfer.side_effect = RetriableError(
            "Connection timeout"
        )

        # Execute and verify exception is raised
        with pytest.raises(RetriableError):
            service.create_transfer(paid_invoice)

        # Verify failed transfer was saved
        mock_repository.create.assert_called_once()
        saved_transfer = mock_repository.create.call_args[0][0]
        assert saved_transfer.status == TransferStatus.FAILED
        assert saved_transfer.error_message == "Connection timeout"
        assert saved_transfer.retry_count == 1
        assert saved_transfer.last_retry_at is not None

        # Verify failure event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert published_event.event_type == TRANSFER_FAILED
        payload = published_event.payload
        assert payload["invoice_id"] == paid_invoice.id
        assert payload["error_message"] == "Connection timeout"

    def test_create_transfer_non_retriable_error(
        self,
        service,
        mock_repository,
        mock_stark_api,
        mock_event_bus,
        paid_invoice,
    ):
        """Test transfer creation with non-retriable error."""
        # Setup: no existing transfer, but API fails with non-retriable error
        mock_repository.get_by_external_id.return_value = None
        mock_stark_api.create_transfer.side_effect = ValidationError("Invalid account")

        # Execute and verify exception is raised
        with pytest.raises(ValidationError):
            service.create_transfer(paid_invoice)

        # Verify failed transfer was saved
        mock_repository.create.assert_called_once()
        saved_transfer = mock_repository.create.call_args[0][0]
        assert saved_transfer.status == TransferStatus.FAILED
        assert saved_transfer.error_message == "Invalid account"

        # Verify failure event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert published_event.event_type == TRANSFER_FAILED

    def test_get_transfer_found(self, service, mock_repository):
        """Test getting a transfer that exists."""
        # Setup
        transfer = TransferModel(
            id="transfer-123",
            invoice_id="invoice-123",
            amount=95.0,
        )
        mock_repository.get_by_id.return_value = transfer

        # Execute
        result = service.get_transfer("transfer-123")

        # Verify
        mock_repository.get_by_id.assert_called_once_with("transfer-123")
        assert result == transfer

    def test_get_transfer_not_found(self, service, mock_repository):
        """Test getting a transfer that doesn't exist."""
        # Setup
        mock_repository.get_by_id.return_value = None

        # Execute
        result = service.get_transfer("nonexistent")

        # Verify
        mock_repository.get_by_id.assert_called_once_with("nonexistent")
        assert result is None

    def test_list_transfers_no_filter(self, service, mock_repository):
        """Test listing transfers without filter."""
        # Setup
        transfers = [
            TransferModel(id="t1", invoice_id="i1", amount=50.0),
            TransferModel(id="t2", invoice_id="i2", amount=75.0),
        ]
        mock_repository.list.return_value = transfers

        # Execute
        result = service.list_transfers()

        # Verify
        mock_repository.list.assert_called_once_with(status=None, limit=100, offset=0)
        assert result == transfers

    def test_list_transfers_with_filter(self, service, mock_repository):
        """Test listing transfers with status filter."""
        # Setup
        transfers = [
            TransferModel(
                id="t1",
                invoice_id="i1",
                amount=50.0,
                status=TransferStatus.CREATED,
            ),
        ]
        mock_repository.list.return_value = transfers

        # Execute
        result = service.list_transfers(status="created", limit=10, offset=5)

        # Verify
        mock_repository.list.assert_called_once_with(
            status="created", limit=10, offset=5
        )
        assert result == transfers

    def test_update_transfer_status_success(self, service, mock_repository):
        """Test updating transfer status."""
        # Setup
        transfer = TransferModel(
            id="transfer-123",
            invoice_id="invoice-123",
            amount=95.0,
            status=TransferStatus.CREATED,
        )
        mock_repository.get_by_id.return_value = transfer

        # Execute
        service.update_transfer_status(
            "transfer-123",
            "processing",
            completed_at=datetime.now(UTC),
        )

        # Verify
        mock_repository.get_by_id.assert_called_once_with("transfer-123")
        mock_repository.update.assert_called_once()
        updated_transfer = mock_repository.update.call_args[0][0]
        assert updated_transfer.status == TransferStatus.PROCESSING
        assert updated_transfer.completed_at is not None
        assert updated_transfer.updated_at is not None

    def test_update_transfer_status_not_found(self, service, mock_repository):
        """Test updating status of non-existent transfer."""
        # Setup
        mock_repository.get_by_id.return_value = None

        # Execute and verify
        with pytest.raises(NotFoundError) as exc_info:
            service.update_transfer_status("nonexistent", "processing")

        assert "Transfer not found" in str(exc_info.value)
        mock_repository.update.assert_not_called()

    def test_create_transfer_amount_conversion(
        self,
        service,
        mock_repository,
        mock_stark_api,
        mock_event_bus,
        paid_invoice,
    ):
        """Test that amount is correctly converted to cents."""
        # Setup
        mock_repository.get_by_external_id.return_value = None
        paid_invoice.net_amount = 123.45

        # Execute
        service.create_transfer(paid_invoice)

        # Verify amount was converted to cents (int)
        call_kwargs = mock_stark_api.create_transfer.call_args[1]
        assert call_kwargs["amount"] == 12345  # 123.45 * 100
        assert isinstance(call_kwargs["amount"], int)

    def test_create_transfer_external_id_format(
        self,
        service,
        mock_repository,
        mock_stark_api,
        paid_invoice,
    ):
        """Test that external_id follows correct format."""
        # Setup
        mock_repository.get_by_external_id.return_value = None

        # Execute
        service.create_transfer(paid_invoice)

        # Verify external_id format
        call_kwargs = mock_stark_api.create_transfer.call_args[1]
        assert call_kwargs["external_id"] == f"invoice-{paid_invoice.id}"

    def test_create_transfer_includes_tags(
        self,
        service,
        mock_repository,
        mock_stark_api,
        paid_invoice,
    ):
        """Test that transfer includes appropriate tags."""
        # Setup
        mock_repository.get_by_external_id.return_value = None

        # Execute
        service.create_transfer(paid_invoice)

        # Verify tags
        call_kwargs = mock_stark_api.create_transfer.call_args[1]
        tags = call_kwargs["tags"]
        assert "invoice-payment" in tags
        assert f"invoice:{paid_invoice.id}" in tags
