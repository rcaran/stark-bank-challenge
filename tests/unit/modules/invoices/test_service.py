"""Unit tests for InvoiceService."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from src.modules.invoices.events import INVOICE_CREATED, INVOICE_CREATION_FAILED
from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.modules.invoices.service import InvoiceService
from src.shared.utils.errors import NotFoundError, StarkBankError, ValidationError


class TestInvoiceService:
    """Tests for InvoiceService."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        return Mock()

    @pytest.fixture
    def mock_stark_api(self):
        """Create mock Stark Bank API."""
        mock = Mock()
        # Default successful response
        mock.create_invoice.return_value = Mock(
            id="stark-invoice-123",
            amount=10000,
            status="created",
        )
        return mock

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return Mock()

    @pytest.fixture
    def service(self, mock_repository, mock_stark_api, mock_event_bus):
        """Create service with mocked dependencies."""
        return InvoiceService(
            repository=mock_repository,
            stark_api=mock_stark_api,
            event_bus=mock_event_bus,
        )

    @pytest.fixture
    def valid_invoice_data(self):
        """Create valid invoice data."""
        return {
            "amount": 10000,
            "customer_name": "João Silva",
            "customer_tax_id": "529.982.247-25",  # Valid CPF
            "customer_email": "joao@example.com",
            "due_date": datetime.now(UTC),
        }

    def test_create_invoice_success(
        self, service, mock_repository, mock_stark_api,
        mock_event_bus, valid_invoice_data,
    ):
        """Test successful invoice creation."""
        result = service.create_invoice(valid_invoice_data)

        # Verify Stark API was called
        mock_stark_api.create_invoice.assert_called_once()

        # Verify invoice was persisted
        mock_repository.create.assert_called_once()
        created_invoice = mock_repository.create.call_args[0][0]
        assert created_invoice.status == InvoiceStatus.CREATED
        assert created_invoice.stark_invoice_id == "stark-invoice-123"

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.event_type == INVOICE_CREATED

        # Verify return value (amount is stored in reais, not cents)
        assert result.amount == 100.0  # 10000 cents = 100.0 reais
        assert result.status == InvoiceStatus.CREATED

    def test_create_invoice_stark_failure(
        self, service, mock_repository, mock_stark_api,
        mock_event_bus, valid_invoice_data,
    ):
        """Test invoice creation when Stark Bank fails."""
        mock_stark_api.create_invoice.side_effect = StarkBankError("Connection failed")

        with pytest.raises(StarkBankError):
            service.create_invoice(valid_invoice_data)

        # Verify failed invoice was saved
        mock_repository.create.assert_called_once()
        saved_invoice = mock_repository.create.call_args[0][0]
        assert saved_invoice.status == InvoiceStatus.FAILED
        assert saved_invoice.error_message == "Connection failed"

        # Verify failure event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.event_type == INVOICE_CREATION_FAILED

    def test_create_invoice_validation_error_missing_amount(self, service):
        """Test validation error for missing amount."""
        invalid_data = {
            "customer_name": "Test",
            "customer_tax_id": "529.982.247-25",
            "customer_email": "test@test.com",
        }

        with pytest.raises(ValidationError, match="Missing required field: amount"):
            service.create_invoice(invalid_data)

    def test_create_invoice_validation_error_invalid_amount(self, service):
        """Test validation error for invalid amount."""
        invalid_data = {
            "amount": -100,
            "customer_name": "Test",
            "customer_tax_id": "529.982.247-25",
            "customer_email": "test@test.com",
        }

        with pytest.raises(ValidationError, match="Amount must be a positive number"):
            service.create_invoice(invalid_data)

    def test_create_invoice_validation_error_invalid_tax_id(self, service):
        """Test validation error for invalid tax ID."""
        invalid_data = {
            "amount": 10000,
            "customer_name": "Test",
            "customer_tax_id": "123.456.789-00",  # Invalid CPF
            "customer_email": "test@test.com",
        }

        with pytest.raises(ValidationError, match="Invalid tax ID"):
            service.create_invoice(invalid_data)

    def test_create_invoice_validation_error_invalid_email(self, service):
        """Test validation error for invalid email."""
        invalid_data = {
            "amount": 10000,
            "customer_name": "Test",
            "customer_tax_id": "529.982.247-25",
            "customer_email": "invalid-email",
        }

        with pytest.raises(ValidationError, match="Invalid email"):
            service.create_invoice(invalid_data)

    def test_get_invoice_found(self, service, mock_repository):
        """Test getting invoice that exists."""
        expected = InvoiceModel(
            id="test-id",
            amount=10000,
            customer_name="Test",
            customer_tax_id="529.982.247-25",
            customer_email="test@test.com",
        )
        mock_repository.get_by_id.return_value = expected

        result = service.get_invoice("test-id")

        assert result == expected
        mock_repository.get_by_id.assert_called_once_with("test-id")

    def test_get_invoice_not_found(self, service, mock_repository):
        """Test getting invoice that doesn't exist."""
        mock_repository.get_by_id.return_value = None

        result = service.get_invoice("nonexistent")

        assert result is None

    def test_get_invoice_by_stark_id(self, service, mock_repository):
        """Test getting invoice by Stark Bank ID."""
        expected = InvoiceModel(
            id="test-id",
            stark_invoice_id="stark-123",
            amount=10000,
            customer_name="Test",
            customer_tax_id="529.982.247-25",
            customer_email="test@test.com",
        )
        mock_repository.get_by_stark_id.return_value = expected

        result = service.get_invoice_by_stark_id("stark-123")

        assert result == expected
        assert result.stark_invoice_id == "stark-123"

    def test_list_invoices(self, service, mock_repository):
        """Test listing invoices."""
        mock_repository.list.return_value = [
            InvoiceModel(
                amount=10000,
                customer_name="Test1",
                customer_tax_id="529.982.247-25",
                customer_email="t1@test.com",
            ),
            InvoiceModel(
                amount=20000,
                customer_name="Test2",
                customer_tax_id="529.982.247-25",
                customer_email="t2@test.com",
            ),
        ]

        result = service.list_invoices(status="pending", limit=10, offset=0)

        assert len(result) == 2
        mock_repository.list.assert_called_once_with(
            status="pending", limit=10, offset=0
        )

    def test_update_invoice_status(self, service, mock_repository):
        """Test updating invoice status."""
        invoice = InvoiceModel(
            id="test-id",
            amount=10000,
            customer_name="Test",
            customer_tax_id="529.982.247-25",
            customer_email="test@test.com",
            status=InvoiceStatus.CREATED,
        )
        mock_repository.get_by_id.return_value = invoice

        result = service.update_invoice_status(
            "test-id",
            InvoiceStatus.PAID,
            fee=500,
        )

        assert result.status == InvoiceStatus.PAID
        assert result.fee == 500
        assert result.net_amount == 9500
        mock_repository.update.assert_called_once()

    def test_update_invoice_status_not_found(self, service, mock_repository):
        """Test updating non-existent invoice."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            service.update_invoice_status("nonexistent", InvoiceStatus.PAID)

    def test_mark_invoice_as_paid(self, service, mock_repository):
        """Test marking invoice as paid."""
        invoice = InvoiceModel(
            id="test-id",
            amount=10000,
            customer_name="Test",
            customer_tax_id="529.982.247-25",
            customer_email="test@test.com",
            status=InvoiceStatus.CREATED,
        )
        mock_repository.get_by_id.return_value = invoice

        paid_at = datetime.now(UTC)
        result = service.mark_invoice_as_paid("test-id", fee=500, paid_at=paid_at)

        assert result.status == InvoiceStatus.PAID
        assert result.fee == 500
        assert result.net_amount == 9500
        assert result.paid_at == paid_at
        mock_repository.update.assert_called_once()

    def test_mark_invoice_as_paid_not_found(self, service, mock_repository):
        """Test marking non-existent invoice as paid."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            service.mark_invoice_as_paid("nonexistent", fee=500)

    def test_count_invoices(self, service, mock_repository):
        """Test counting invoices."""
        mock_repository.count.return_value = 42

        result = service.count_invoices(status="paid")

        assert result == 42
        mock_repository.count.assert_called_once_with(status="paid")


class TestInvoiceServiceValidation:
    """Tests for InvoiceService input validation."""

    @pytest.fixture
    def service(self):
        """Create service with mocks."""
        return InvoiceService(
            repository=Mock(),
            stark_api=Mock(),
            event_bus=Mock(),
        )

    def test_validate_missing_customer_name(self, service):
        """Test validation for missing customer name."""
        data = {
            "amount": 10000,
            "customer_tax_id": "529.982.247-25",
            "customer_email": "test@test.com",
        }

        with pytest.raises(
            ValidationError,
            match="Missing required field: customer_name",
        ):
            service.create_invoice(data)

    def test_validate_empty_customer_name(self, service):
        """Test validation for empty customer name."""
        data = {
            "amount": 10000,
            "customer_name": "",
            "customer_tax_id": "529.982.247-25",
            "customer_email": "test@test.com",
        }

        with pytest.raises(
            ValidationError,
            match="Missing required field: customer_name",
        ):
            service.create_invoice(data)

    def test_validate_valid_cnpj(self, service):
        """Test validation accepts valid CNPJ."""
        mock_stark = service.stark_api
        mock_stark.create_invoice.return_value = Mock(id="stark-123")

        data = {
            "amount": 10000,
            "customer_name": "Test Company",
            "customer_tax_id": "11.222.333/0001-81",  # Valid CNPJ
            "customer_email": "test@company.com",
        }

        # Should not raise ValidationError for tax_id
        service.create_invoice(data)
        mock_stark.create_invoice.assert_called_once()
