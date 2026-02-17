"""Unit tests for InvoiceRepository."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock

import pytest

from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.modules.invoices.repository import InvoiceRepository
from src.shared.utils.errors import NotFoundError


class TestInvoiceRepository:
    """Tests for InvoiceRepository."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database connection."""
        mock = Mock()
        mock.get_db.return_value.__enter__ = Mock(return_value=Mock())
        mock.get_db.return_value.__exit__ = Mock(return_value=False)
        return mock

    @pytest.fixture
    def repository(self, mock_db):
        """Create repository with mocked database."""
        return InvoiceRepository(db_connection=mock_db)

    @pytest.fixture
    def sample_invoice(self):
        """Create a sample invoice for testing."""
        return InvoiceModel(
            id="test-invoice-123",
            amount=10000,
            customer_name="Test User",
            customer_tax_id="123.456.789-09",
            customer_email="test@test.com",
            status=InvoiceStatus.PENDING,
        )

    def test_create_invoice(self, repository, mock_db, sample_invoice):
        """Test creating an invoice in the database."""
        # Setup mock
        mock_conn = MagicMock()
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        # Execute
        repository.create(sample_invoice)

        # Verify execute was called
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "INSERT INTO invoices" in query
        assert params[0] == sample_invoice.id
        assert params[2] == sample_invoice.amount

    def test_get_by_id_found(self, repository, mock_db):
        """Test getting invoice by ID when found."""
        # Setup mock row
        mock_row = (
            "invoice-id",
            "stark-id",
            10000,
            "Test User",
            "123.456.789-09",
            "test@test.com",
            "pending",
            datetime.now(UTC).isoformat(),
            None,  # paid_at
            None,  # fee
            None,  # net_amount
            0,  # retry_count
            None,  # last_retry_at
            None,  # error_message
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        # Execute
        result = repository.get_by_id("invoice-id")

        # Verify
        assert result is not None
        assert result.id == "invoice-id"
        assert result.stark_invoice_id == "stark-id"
        assert result.amount == 10000

    def test_get_by_id_not_found(self, repository, mock_db):
        """Test getting invoice by ID when not found."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.get_by_id("nonexistent-id")

        assert result is None

    def test_get_by_stark_id(self, repository, mock_db):
        """Test getting invoice by Stark Bank ID."""
        mock_row = (
            "invoice-id",
            "stark-123",
            15000,
            "Test User",
            "123.456.789-09",
            "test@test.com",
            "created",
            datetime.now(UTC).isoformat(),
            None,
            None,
            None,
            0,
            None,
            None,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.get_by_stark_id("stark-123")

        assert result is not None
        assert result.stark_invoice_id == "stark-123"
        mock_conn.execute.assert_called_once()

    def test_update_invoice(self, repository, mock_db, sample_invoice):
        """Test updating an invoice."""
        # First mock for get_by_id (to check existence)
        existing_row = (
            sample_invoice.id,
            None,
            10000,
            "Test User",
            "123.456.789-09",
            "test@test.com",
            "pending",
            datetime.now(UTC).isoformat(),
            None,
            None,
            None,
            0,
            None,
            None,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # First call returns existing, second call is the update
        mock_cursor.fetchone.return_value = existing_row
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        # Update the invoice
        sample_invoice.status = InvoiceStatus.CREATED
        sample_invoice.stark_invoice_id = "new-stark-id"

        repository.update(sample_invoice)

        # Verify update was called (second execute call)
        assert mock_conn.execute.call_count == 2

    def test_update_invoice_not_found(self, repository, mock_db, sample_invoice):
        """Test updating non-existent invoice raises error."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        with pytest.raises(NotFoundError):
            repository.update(sample_invoice)

    def test_list_invoices(self, repository, mock_db):
        """Test listing invoices."""
        mock_rows = [
            (
                "id1",
                "stark1",
                10000,
                "User1",
                "111.111.111-11",
                "u1@test.com",
                "pending",
                datetime.now(UTC).isoformat(),
                None,
                None,
                None,
                0,
                None,
                None,
            ),
            (
                "id2",
                "stark2",
                20000,
                "User2",
                "222.222.222-22",
                "u2@test.com",
                "created",
                datetime.now(UTC).isoformat(),
                None,
                None,
                None,
                0,
                None,
                None,
            ),
        ]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.list(limit=10, offset=0)

        assert len(result) == 2
        assert result[0].id == "id1"
        assert result[1].id == "id2"

    def test_list_invoices_with_status_filter(self, repository, mock_db):
        """Test listing invoices with status filter."""
        mock_rows = [
            (
                "id1",
                "stark1",
                10000,
                "User1",
                "111.111.111-11",
                "u1@test.com",
                "paid",
                datetime.now(UTC).isoformat(),
                datetime.now(UTC).isoformat(),
                500,
                9500,
                0,
                None,
                None,
            ),
        ]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.list(status="paid", limit=10, offset=0)

        assert len(result) == 1
        assert result[0].status == InvoiceStatus.PAID

        # Verify query includes status filter
        call_args = mock_conn.execute.call_args
        query = call_args[0][0]
        assert "WHERE status = ?" in query

    def test_count_invoices(self, repository, mock_db):
        """Test counting invoices."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.count()

        assert result == 42

    def test_count_invoices_with_status(self, repository, mock_db):
        """Test counting invoices with status filter."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (15,)
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.count(status="paid")

        assert result == 15

    def test_list_by_status(self, repository, mock_db):
        """Test listing invoices by status."""
        mock_rows = [
            (
                "id1",
                None,
                10000,
                "User1",
                "111.111.111-11",
                "u1@test.com",
                "pending",
                datetime.now(UTC).isoformat(),
                None,
                None,
                None,
                0,
                None,
                None,
            ),
        ]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.list_by_status(InvoiceStatus.PENDING)

        assert len(result) == 1
        assert result[0].status == InvoiceStatus.PENDING
