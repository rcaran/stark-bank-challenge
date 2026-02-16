"""Unit tests for InvoiceWebhookProcessor."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.modules.webhooks.events import INVOICE_PAID
from src.modules.webhooks.invoice_processor import InvoiceWebhookProcessor
from src.modules.webhooks.models import InvoiceWebhookPayload
from src.shared.utils.errors import NotFoundError


class TestInvoiceWebhookProcessor:
    """Tests for InvoiceWebhookProcessor class."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock invoice repository."""
        return Mock()

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return Mock()

    @pytest.fixture
    def processor(self, mock_repository, mock_event_bus):
        """Create processor with mocked dependencies."""
        return InvoiceWebhookProcessor(
            invoice_repository=mock_repository,
            event_bus=mock_event_bus,
        )

    @pytest.fixture
    def sample_invoice(self):
        """Create sample invoice model."""
        return InvoiceModel(
            id="inv-123",
            stark_invoice_id="stark-invoice-456",
            amount=100.00,
            customer_name="João Silva",
            customer_tax_id="529.982.247-25",
            customer_email="joao@example.com",
            status=InvoiceStatus.CREATED,
            created_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
        )

    @pytest.fixture
    def paid_webhook_payload(self):
        """Create sample paid invoice webhook payload."""
        return InvoiceWebhookPayload(
            invoice_id="stark-invoice-456",
            status="credited",
            amount=10000,  # 100.00 in centavos
            fee=50,  # 0.50 in centavos
            name="João Silva",
            tax_id="529.982.247-25",
            created=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
            updated=datetime(2026, 2, 16, 14, 30, 0, tzinfo=UTC),
        )

    @pytest.fixture
    def created_webhook_payload(self):
        """Create sample created invoice webhook payload (not paid)."""
        return InvoiceWebhookPayload(
            invoice_id="stark-invoice-456",
            status="created",
            amount=10000,
            fee=None,
            name="João Silva",
            tax_id="529.982.247-25",
        )

    # ==========================================================================
    # process() tests
    # ==========================================================================

    def test_process_paid_invoice_success(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_invoice,
        paid_webhook_payload,
    ):
        """Test successful processing of paid invoice webhook."""
        mock_repository.get_by_stark_id.return_value = sample_invoice

        processor.process(paid_webhook_payload)

        # Verify repository was called to find invoice
        mock_repository.get_by_stark_id.assert_called_once_with("stark-invoice-456")

        # Verify invoice was updated
        mock_repository.update.assert_called_once()
        updated_invoice = mock_repository.update.call_args[0][0]
        assert updated_invoice.status == InvoiceStatus.PAID
        assert updated_invoice.fee == 0.50  # 50 centavos = 0.50 reais
        assert updated_invoice.net_amount == 99.50  # 100.00 - 0.50
        assert updated_invoice.paid_at is not None

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.event_type == INVOICE_PAID
        assert event.payload["invoice_id"] == "inv-123"
        assert event.payload["stark_invoice_id"] == "stark-invoice-456"
        assert event.payload["amount"] == 100.00
        assert event.payload["fee"] == 0.50
        assert event.payload["net_amount"] == 99.50

    def test_process_non_payment_webhook_ignored(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        created_webhook_payload,
    ):
        """Test that non-payment webhooks are ignored."""
        processor.process(created_webhook_payload)

        # Repository should not be queried for non-payment events
        mock_repository.get_by_stark_id.assert_not_called()
        mock_repository.update.assert_not_called()
        mock_event_bus.publish.assert_not_called()

    def test_process_invoice_not_found_raises_error(
        self,
        processor,
        mock_repository,
        paid_webhook_payload,
    ):
        """Test that NotFoundError is raised when invoice not found."""
        mock_repository.get_by_stark_id.return_value = None

        with pytest.raises(NotFoundError, match="Invoice not found"):
            processor.process(paid_webhook_payload)

    def test_process_calculates_net_amount_correctly(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_invoice,
    ):
        """Test that net amount is calculated correctly."""
        mock_repository.get_by_stark_id.return_value = sample_invoice

        payload = InvoiceWebhookPayload(
            invoice_id="stark-invoice-456",
            status="credited",
            amount=50000,  # 500.00 reais
            fee=250,  # 2.50 reais
            name="Test",
            tax_id="12345678900",
        )
        # Update sample invoice amount to match
        sample_invoice.amount = 500.00

        processor.process(payload)

        updated_invoice = mock_repository.update.call_args[0][0]
        assert updated_invoice.fee == 2.50
        assert updated_invoice.net_amount == 497.50  # 500.00 - 2.50

    def test_process_sets_paid_at_timestamp(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_invoice,
        paid_webhook_payload,
    ):
        """Test that paid_at timestamp is set from webhook."""
        mock_repository.get_by_stark_id.return_value = sample_invoice

        processor.process(paid_webhook_payload)

        updated_invoice = mock_repository.update.call_args[0][0]
        assert updated_invoice.paid_at == datetime(
            2026, 2, 16, 14, 30, 0, tzinfo=UTC
        )

    def test_process_sets_current_time_when_updated_missing(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_invoice,
    ):
        """Test that current time is used when webhook has no updated field."""
        mock_repository.get_by_stark_id.return_value = sample_invoice

        payload = InvoiceWebhookPayload(
            invoice_id="stark-invoice-456",
            status="credited",
            amount=10000,
            fee=50,
            name="Test",
            tax_id="12345678900",
            updated=None,  # No updated timestamp
        )

        processor.process(payload)

        updated_invoice = mock_repository.update.call_args[0][0]
        assert updated_invoice.paid_at is not None
        # Should be close to now
        time_diff = abs(
            (datetime.now(UTC) - updated_invoice.paid_at).total_seconds()
        )
        assert time_diff < 5  # Within 5 seconds

    def test_process_handles_zero_fee(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_invoice,
    ):
        """Test processing when fee is zero."""
        mock_repository.get_by_stark_id.return_value = sample_invoice

        payload = InvoiceWebhookPayload(
            invoice_id="stark-invoice-456",
            status="credited",
            amount=10000,
            fee=0,  # Zero fee
            name="Test",
            tax_id="12345678900",
        )

        processor.process(payload)

        updated_invoice = mock_repository.update.call_args[0][0]
        assert updated_invoice.fee == 0.0
        assert updated_invoice.net_amount == 100.00  # Full amount

    def test_process_handles_null_fee(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_invoice,
    ):
        """Test processing when fee is None."""
        mock_repository.get_by_stark_id.return_value = sample_invoice

        payload = InvoiceWebhookPayload(
            invoice_id="stark-invoice-456",
            status="credited",
            amount=10000,
            fee=None,  # No fee
            name="Test",
            tax_id="12345678900",
        )

        processor.process(payload)

        updated_invoice = mock_repository.update.call_args[0][0]
        assert updated_invoice.fee is None
        # net_amount should be None when fee is not set
        assert updated_invoice.net_amount is None

    def test_process_event_metadata_contains_source(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_invoice,
        paid_webhook_payload,
    ):
        """Test that event metadata contains webhook source info."""
        mock_repository.get_by_stark_id.return_value = sample_invoice

        processor.process(paid_webhook_payload)

        event = mock_event_bus.publish.call_args[0][0]
        assert event.metadata["source"] == "webhook"
        assert event.metadata["webhook_invoice_id"] == "stark-invoice-456"

    # ==========================================================================
    # process_payment() tests
    # ==========================================================================

    def test_process_payment_success(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_invoice,
    ):
        """Test direct payment processing."""
        mock_repository.get_by_stark_id.return_value = sample_invoice

        result = processor.process_payment(
            stark_invoice_id="stark-invoice-456",
            amount=10000,
            fee=100,  # 1.00 real
            paid_at=datetime(2026, 2, 16, 12, 0, 0, tzinfo=UTC),
        )

        # Verify invoice was updated
        assert result.status == InvoiceStatus.PAID
        assert result.fee == 1.00
        assert result.paid_at == datetime(2026, 2, 16, 12, 0, 0, tzinfo=UTC)

        # Verify repository was called
        mock_repository.update.assert_called_once()

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.event_type == INVOICE_PAID
        assert event.metadata["source"] == "direct"

    def test_process_payment_invoice_not_found(
        self,
        processor,
        mock_repository,
    ):
        """Test payment processing when invoice not found."""
        mock_repository.get_by_stark_id.return_value = None

        with pytest.raises(NotFoundError, match="Invoice not found"):
            processor.process_payment(
                stark_invoice_id="non-existent",
                amount=10000,
                fee=100,
            )

    def test_process_payment_uses_current_time_when_not_provided(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_invoice,
    ):
        """Test that current time is used when paid_at not provided."""
        mock_repository.get_by_stark_id.return_value = sample_invoice

        result = processor.process_payment(
            stark_invoice_id="stark-invoice-456",
            amount=10000,
            fee=100,
            paid_at=None,
        )

        # Should be close to now
        time_diff = abs(
            (datetime.now(UTC) - result.paid_at).total_seconds()
        )
        assert time_diff < 5

    # ==========================================================================
    # Edge cases
    # ==========================================================================

    def test_process_canceled_webhook_ignored(
        self,
        processor,
        mock_repository,
        mock_event_bus,
    ):
        """Test that canceled invoice webhooks are ignored."""
        payload = InvoiceWebhookPayload(
            invoice_id="stark-invoice-456",
            status="canceled",
            amount=10000,
            fee=None,
            name="Test",
            tax_id="12345678900",
        )

        processor.process(payload)

        mock_repository.get_by_stark_id.assert_not_called()
        mock_event_bus.publish.assert_not_called()

    def test_process_expired_webhook_ignored(
        self,
        processor,
        mock_repository,
        mock_event_bus,
    ):
        """Test that expired invoice webhooks are ignored."""
        payload = InvoiceWebhookPayload(
            invoice_id="stark-invoice-456",
            status="expired",
            amount=10000,
            fee=None,
            name="Test",
            tax_id="12345678900",
        )

        processor.process(payload)

        mock_repository.get_by_stark_id.assert_not_called()
        mock_event_bus.publish.assert_not_called()

    def test_process_updates_correct_invoice_fields(
        self,
        processor,
        mock_repository,
        mock_event_bus,
        sample_invoice,
        paid_webhook_payload,
    ):
        """Test that only payment-related fields are updated."""
        original_name = sample_invoice.customer_name
        original_email = sample_invoice.customer_email
        original_amount = sample_invoice.amount
        original_created_at = sample_invoice.created_at

        mock_repository.get_by_stark_id.return_value = sample_invoice

        processor.process(paid_webhook_payload)

        updated_invoice = mock_repository.update.call_args[0][0]

        # These fields should NOT change
        assert updated_invoice.customer_name == original_name
        assert updated_invoice.customer_email == original_email
        assert updated_invoice.amount == original_amount
        assert updated_invoice.created_at == original_created_at

        # These fields SHOULD change
        assert updated_invoice.status == InvoiceStatus.PAID
        assert updated_invoice.paid_at is not None
        assert updated_invoice.fee is not None
