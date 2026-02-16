"""Unit tests for TransferHandler."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.modules.transfers.handler import TransferHandler
from src.modules.transfers.models import TransferModel, TransferStatus
from src.shared.events.types import Event, EventType
from src.shared.utils.errors import NotFoundError, ValidationError


class TestTransferHandler:
    """Tests for TransferHandler."""

    @pytest.fixture
    def mock_service(self):
        """Create mock TransferService."""
        mock = Mock()
        # Default successful response
        mock.create_transfer.return_value = TransferModel(
            id="test-transfer-id",
            invoice_id="test-invoice-id",
            amount=95.0,
            external_id="invoice-test-invoice-id",
            status=TransferStatus.CREATED,
            stark_transfer_id="stark-transfer-123",
        )
        return mock

    @pytest.fixture
    def mock_invoice_repository(self):
        """Create mock InvoiceRepository."""
        return Mock()

    @pytest.fixture
    def handler(self, mock_service, mock_invoice_repository):
        """Create handler with mocked dependencies."""
        return TransferHandler(
            service=mock_service,
            invoice_repository=mock_invoice_repository,
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

    @pytest.fixture
    def invoice_paid_event(self):
        """Create an invoice.paid event."""
        return Event(
            event_type=EventType.INVOICE_PAID,
            payload={
                "invoice_id": "test-invoice-id",
                "stark_invoice_id": "stark-invoice-123",
                "amount": 100.0,
                "fee": 5.0,
                "net_amount": 95.0,
            },
        )

    def test_handle_invoice_paid_success(
        self,
        handler,
        mock_service,
        mock_invoice_repository,
        paid_invoice,
        invoice_paid_event,
    ):
        """Test successful handling of invoice.paid event."""
        # Setup: invoice exists and is paid
        mock_invoice_repository.get_by_id.return_value = paid_invoice

        # Execute
        handler.handle_invoice_paid(invoice_paid_event)

        # Verify invoice was loaded
        mock_invoice_repository.get_by_id.assert_called_once_with("test-invoice-id")

        # Verify transfer was created
        mock_service.create_transfer.assert_called_once_with(paid_invoice)

    def test_handle_invoice_paid_missing_invoice_id(
        self,
        handler,
        mock_service,
        mock_invoice_repository,
    ):
        """Test handling event with missing invoice_id."""
        # Setup: event without invoice_id
        event = Event(
            event_type=EventType.INVOICE_PAID,
            payload={},
        )

        # Execute
        handler.handle_invoice_paid(event)

        # Verify no repository or service calls
        mock_invoice_repository.get_by_id.assert_not_called()
        mock_service.create_transfer.assert_not_called()

    def test_handle_invoice_paid_invoice_not_found(
        self,
        handler,
        mock_service,
        mock_invoice_repository,
        invoice_paid_event,
    ):
        """Test handling event when invoice is not found in database."""
        # Setup: invoice not found
        mock_invoice_repository.get_by_id.side_effect = NotFoundError(
            "Invoice not found"
        )

        # Execute (should not raise exception)
        handler.handle_invoice_paid(invoice_paid_event)

        # Verify invoice was attempted to load
        mock_invoice_repository.get_by_id.assert_called_once_with("test-invoice-id")

        # Verify no transfer was created
        mock_service.create_transfer.assert_not_called()

    def test_handle_invoice_paid_invoice_not_paid_status(
        self,
        handler,
        mock_service,
        mock_invoice_repository,
        invoice_paid_event,
    ):
        """Test handling event when invoice is not in PAID status."""
        # Setup: invoice exists but not paid
        unpaid_invoice = InvoiceModel(
            id="test-invoice-id",
            amount=100.0,
            customer_name="João Silva",
            customer_tax_id="529.982.247-25",
            customer_email="joao@example.com",
            status=InvoiceStatus.CREATED,  # Not PAID
        )
        mock_invoice_repository.get_by_id.return_value = unpaid_invoice

        # Execute
        handler.handle_invoice_paid(invoice_paid_event)

        # Verify invoice was loaded
        mock_invoice_repository.get_by_id.assert_called_once_with("test-invoice-id")

        # Verify no transfer was created
        mock_service.create_transfer.assert_not_called()

    def test_handle_invoice_paid_invalid_net_amount(
        self,
        handler,
        mock_service,
        mock_invoice_repository,
        invoice_paid_event,
    ):
        """Test handling event when invoice has invalid net_amount."""
        # Setup: invoice with zero net_amount
        invalid_invoice = InvoiceModel(
            id="test-invoice-id",
            amount=100.0,
            customer_name="João Silva",
            customer_tax_id="529.982.247-25",
            customer_email="joao@example.com",
            status=InvoiceStatus.PAID,
            paid_at=datetime.now(UTC),
            fee=5.0,
            net_amount=0.0,  # Invalid
        )
        mock_invoice_repository.get_by_id.return_value = invalid_invoice

        # Execute
        handler.handle_invoice_paid(invoice_paid_event)

        # Verify invoice was loaded
        mock_invoice_repository.get_by_id.assert_called_once_with("test-invoice-id")

        # Verify no transfer was created
        mock_service.create_transfer.assert_not_called()

    def test_handle_invoice_paid_service_raises_exception(
        self,
        handler,
        mock_service,
        mock_invoice_repository,
        paid_invoice,
        invoice_paid_event,
    ):
        """Test handling event when service raises exception."""
        # Setup: invoice exists but service fails
        mock_invoice_repository.get_by_id.return_value = paid_invoice
        mock_service.create_transfer.side_effect = ValidationError(
            "Transfer creation failed"
        )

        # Execute (should not raise exception - should be caught and logged)
        handler.handle_invoice_paid(invoice_paid_event)

        # Verify invoice was loaded
        mock_invoice_repository.get_by_id.assert_called_once_with("test-invoice-id")

        # Verify transfer creation was attempted
        mock_service.create_transfer.assert_called_once_with(paid_invoice)

    def test_handle_invoice_paid_with_none_net_amount(
        self,
        handler,
        mock_service,
        mock_invoice_repository,
        invoice_paid_event,
    ):
        """Test handling event when invoice has None net_amount."""
        # Setup: invoice with None net_amount
        invoice_no_net_amount = InvoiceModel(
            id="test-invoice-id",
            amount=100.0,
            customer_name="João Silva",
            customer_tax_id="529.982.247-25",
            customer_email="joao@example.com",
            status=InvoiceStatus.PAID,
            paid_at=datetime.now(UTC),
            fee=5.0,
            net_amount=None,  # None
        )
        mock_invoice_repository.get_by_id.return_value = invoice_no_net_amount

        # Execute
        handler.handle_invoice_paid(invoice_paid_event)

        # Verify invoice was loaded
        mock_invoice_repository.get_by_id.assert_called_once_with("test-invoice-id")

        # Verify no transfer was created
        mock_service.create_transfer.assert_not_called()

    def test_handler_initialization(self, mock_service, mock_invoice_repository):
        """Test handler initialization."""
        handler = TransferHandler(
            service=mock_service,
            invoice_repository=mock_invoice_repository,
        )

        assert handler.service == mock_service
        assert handler.invoice_repository == mock_invoice_repository
