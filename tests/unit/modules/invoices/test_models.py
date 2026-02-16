"""Unit tests for InvoiceModel."""

import uuid
from datetime import datetime, timezone

import pytest

from src.modules.invoices.models import InvoiceModel, InvoiceStatus


class TestInvoiceModel:
    """Tests for InvoiceModel dataclass."""

    def test_create_invoice_with_required_fields(self):
        """Test creating invoice with required fields."""
        invoice = InvoiceModel(
            amount=10000,
            customer_name="João Silva",
            customer_tax_id="123.456.789-09",
            customer_email="joao@example.com",
        )

        assert invoice.amount == 10000
        assert invoice.customer_name == "João Silva"
        assert invoice.customer_tax_id == "123.456.789-09"
        assert invoice.customer_email == "joao@example.com"
        assert invoice.status == InvoiceStatus.PENDING
        assert invoice.id is not None
        assert invoice.created_at is not None

    def test_create_invoice_with_all_fields(self):
        """Test creating invoice with all fields."""
        custom_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        due_date = datetime.now(timezone.utc)

        invoice = InvoiceModel(
            id=custom_id,
            amount=50000,
            customer_name="Maria Santos",
            customer_tax_id="12.345.678/0001-90",
            customer_email="maria@company.com",
            status=InvoiceStatus.CREATED,
            created_at=created_at,
            due_date=due_date,
            stark_invoice_id="stark-123",
        )

        assert invoice.id == custom_id
        assert invoice.amount == 50000
        assert invoice.status == InvoiceStatus.CREATED
        assert invoice.stark_invoice_id == "stark-123"

    def test_create_invoice_invalid_amount(self):
        """Test that negative amount raises ValueError."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            InvoiceModel(
                amount=-100,
                customer_name="Test",
                customer_tax_id="123.456.789-09",
                customer_email="test@test.com",
            )

    def test_create_invoice_zero_amount(self):
        """Test that zero amount raises ValueError."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            InvoiceModel(
                amount=0,
                customer_name="Test",
                customer_tax_id="123.456.789-09",
                customer_email="test@test.com",
            )

    def test_create_invoice_empty_name(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Customer name is required"):
            InvoiceModel(
                amount=1000,
                customer_name="",
                customer_tax_id="123.456.789-09",
                customer_email="test@test.com",
            )

    def test_create_invoice_empty_tax_id(self):
        """Test that empty tax ID raises ValueError."""
        with pytest.raises(ValueError, match="Customer tax ID is required"):
            InvoiceModel(
                amount=1000,
                customer_name="Test",
                customer_tax_id="",
                customer_email="test@test.com",
            )

    def test_create_invoice_empty_email(self):
        """Test that empty email raises ValueError."""
        with pytest.raises(ValueError, match="Customer email is required"):
            InvoiceModel(
                amount=1000,
                customer_name="Test",
                customer_tax_id="123.456.789-09",
                customer_email="",
            )

    def test_calculate_net_amount(self):
        """Test net amount calculation."""
        invoice = InvoiceModel(
            amount=10000,
            customer_name="Test",
            customer_tax_id="123.456.789-09",
            customer_email="test@test.com",
        )

        invoice.fee = 500
        net = invoice.calculate_net_amount()

        assert net == 9500
        assert invoice.net_amount == 9500

    def test_calculate_net_amount_no_fee(self):
        """Test net amount calculation with no fee."""
        invoice = InvoiceModel(
            amount=10000,
            customer_name="Test",
            customer_tax_id="123.456.789-09",
            customer_email="test@test.com",
        )

        net = invoice.calculate_net_amount()

        assert net is None
        assert invoice.net_amount is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        invoice = InvoiceModel(
            amount=10000,
            customer_name="Test User",
            customer_tax_id="123.456.789-09",
            customer_email="test@test.com",
        )

        data = invoice.to_dict()

        assert data["id"] == invoice.id
        assert data["amount"] == 10000
        assert data["customer_name"] == "Test User"
        assert data["customer_tax_id"] == "123.456.789-09"
        assert data["customer_email"] == "test@test.com"
        assert data["status"] == "pending"
        assert data["created_at"] is not None

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "id": "test-id-123",
            "amount": 25000,
            "customer_name": "From Dict User",
            "customer_tax_id": "123.456.789-09",
            "customer_email": "from_dict@test.com",
            "status": "created",
            "stark_invoice_id": "stark-456",
        }

        invoice = InvoiceModel.from_dict(data)

        assert invoice.id == "test-id-123"
        assert invoice.amount == 25000
        assert invoice.customer_name == "From Dict User"
        assert invoice.status == InvoiceStatus.CREATED
        assert invoice.stark_invoice_id == "stark-456"

    def test_from_dict_with_datetime_strings(self):
        """Test creation from dict with datetime strings."""
        created = datetime.now(timezone.utc)
        paid = datetime.now(timezone.utc)

        data = {
            "amount": 10000,
            "customer_name": "Test",
            "customer_tax_id": "123.456.789-09",
            "customer_email": "test@test.com",
            "created_at": created.isoformat(),
            "paid_at": paid.isoformat(),
        }

        invoice = InvoiceModel.from_dict(data)

        assert invoice.created_at is not None
        assert invoice.paid_at is not None

    def test_mark_as_created(self):
        """Test marking invoice as created."""
        invoice = InvoiceModel(
            amount=10000,
            customer_name="Test",
            customer_tax_id="123.456.789-09",
            customer_email="test@test.com",
        )

        invoice.mark_as_created("stark-id-789")

        assert invoice.status == InvoiceStatus.CREATED
        assert invoice.stark_invoice_id == "stark-id-789"
        assert invoice.error_message is None

    def test_mark_as_paid(self):
        """Test marking invoice as paid."""
        invoice = InvoiceModel(
            amount=10000,
            customer_name="Test",
            customer_tax_id="123.456.789-09",
            customer_email="test@test.com",
        )

        paid_at = datetime.now(timezone.utc)
        invoice.mark_as_paid(fee=500, paid_at=paid_at)

        assert invoice.status == InvoiceStatus.PAID
        assert invoice.fee == 500
        assert invoice.net_amount == 9500
        assert invoice.paid_at == paid_at

    def test_mark_as_failed(self):
        """Test marking invoice as failed."""
        invoice = InvoiceModel(
            amount=10000,
            customer_name="Test",
            customer_tax_id="123.456.789-09",
            customer_email="test@test.com",
        )

        invoice.mark_as_failed("Connection timeout")

        assert invoice.status == InvoiceStatus.FAILED
        assert invoice.error_message == "Connection timeout"
        assert invoice.retry_count == 1
        assert invoice.last_retry_at is not None

    def test_status_string_conversion(self):
        """Test that status string is converted to enum."""
        data = {
            "amount": 10000,
            "customer_name": "Test",
            "customer_tax_id": "123.456.789-09",
            "customer_email": "test@test.com",
            "status": "paid",
        }

        invoice = InvoiceModel.from_dict(data)

        assert invoice.status == InvoiceStatus.PAID
        assert isinstance(invoice.status, InvoiceStatus)


class TestInvoiceStatus:
    """Tests for InvoiceStatus enum."""

    def test_all_status_values(self):
        """Test all status values exist."""
        assert InvoiceStatus.PENDING.value == "pending"
        assert InvoiceStatus.CREATED.value == "created"
        assert InvoiceStatus.PAID.value == "paid"
        assert InvoiceStatus.CANCELED.value == "canceled"
        assert InvoiceStatus.OVERDUE.value == "overdue"
        assert InvoiceStatus.EXPIRED.value == "expired"
        assert InvoiceStatus.FAILED.value == "failed"

    def test_status_from_string(self):
        """Test creating status from string."""
        status = InvoiceStatus("pending")
        assert status == InvoiceStatus.PENDING

    def test_invalid_status(self):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError):
            InvoiceStatus("invalid_status")
