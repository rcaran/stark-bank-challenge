"""Unit tests for TransferRepository."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock

import pytest

from src.modules.transfers.models import TransferModel, TransferStatus
from src.modules.transfers.repository import TransferRepository
from src.shared.utils.errors import NotFoundError


class TestTransferRepository:
    """Tests for TransferRepository."""

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
        return TransferRepository(db_connection=mock_db)

    @pytest.fixture
    def sample_transfer(self):
        """Create a sample transfer for testing."""
        return TransferModel(
            id="test-transfer-123",
            invoice_id="test-invoice-123",
            external_id="ext-transfer-123",
            amount=9500,
            status=TransferStatus.PENDING,
        )

    def test_create_transfer(self, repository, mock_db, sample_transfer):
        """Test creating a transfer in the database."""
        # Setup mock
        mock_conn = MagicMock()
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        # Execute
        repository.create(sample_transfer)

        # Verify execute was called
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "INSERT INTO transfers" in query
        assert params[0] == sample_transfer.id
        assert params[1] == sample_transfer.invoice_id
        assert params[4] == sample_transfer.amount

    def test_get_by_id_found(self, repository, mock_db):
        """Test getting transfer by ID when found."""
        # Setup mock row
        mock_row = (
            "transfer-id",
            "invoice-id",
            "stark-id",
            "external-id",
            9500,
            "created",
            datetime.now(UTC).isoformat(),
            datetime.now(UTC).isoformat(),
            None,  # completed_at
            0,     # retry_count
            None,  # last_retry_at
            None,  # error_message
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        # Execute
        result = repository.get_by_id("transfer-id")

        # Verify
        assert result is not None
        assert result.id == "transfer-id"
        assert result.invoice_id == "invoice-id"
        assert result.stark_transfer_id == "stark-id"
        assert result.external_id == "external-id"
        assert result.amount == 9500

    def test_get_by_id_not_found(self, repository, mock_db):
        """Test getting transfer by ID when not found."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.get_by_id("nonexistent-id")

        assert result is None

    def test_get_by_stark_id(self, repository, mock_db):
        """Test getting transfer by Stark Bank ID."""
        mock_row = (
            "transfer-id",
            "invoice-id",
            "stark-123",
            "external-id",
            9500,
            "processing",
            datetime.now(UTC).isoformat(),
            datetime.now(UTC).isoformat(),
            None, 0, None, None,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.get_by_stark_id("stark-123")

        assert result is not None
        assert result.stark_transfer_id == "stark-123"
        mock_conn.execute.assert_called_once()

    def test_get_by_external_id(self, repository, mock_db):
        """Test getting transfer by external ID (idempotency)."""
        mock_row = (
            "transfer-id",
            "invoice-id",
            "stark-123",
            "external-123",
            9500,
            "created",
            datetime.now(UTC).isoformat(),
            datetime.now(UTC).isoformat(),
            None, 0, None, None,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.get_by_external_id("external-123")

        assert result is not None
        assert result.external_id == "external-123"
        mock_conn.execute.assert_called_once()

    def test_get_by_invoice_id(self, repository, mock_db):
        """Test getting transfer by invoice ID."""
        mock_row = (
            "transfer-id",
            "invoice-456",
            "stark-123",
            "external-id",
            9500,
            "success",
            datetime.now(UTC).isoformat(),
            datetime.now(UTC).isoformat(),
            datetime.now(UTC).isoformat(),
            0, None, None,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.get_by_invoice_id("invoice-456")

        assert result is not None
        assert result.invoice_id == "invoice-456"
        mock_conn.execute.assert_called_once()

    def test_update_transfer(self, repository, mock_db, sample_transfer):
        """Test updating a transfer."""
        # First mock for get_by_id (to check existence)
        existing_row = (
            sample_transfer.id,
            sample_transfer.invoice_id,
            None,  # stark_transfer_id
            sample_transfer.external_id,
            sample_transfer.amount,
            "pending",
            datetime.now(UTC).isoformat(),
            datetime.now(UTC).isoformat(),
            None, 0, None, None,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # First call returns existing, second call is the update
        mock_cursor.fetchone.return_value = existing_row
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        # Update the transfer
        sample_transfer.status = TransferStatus.CREATED
        sample_transfer.stark_transfer_id = "new-stark-id"

        repository.update(sample_transfer)

        # Verify update was called (second execute call)
        assert mock_conn.execute.call_count == 2

    def test_update_transfer_not_found(self, repository, mock_db, sample_transfer):
        """Test updating non-existent transfer raises error."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        with pytest.raises(NotFoundError):
            repository.update(sample_transfer)

    def test_list_transfers(self, repository, mock_db):
        """Test listing transfers."""
        mock_rows = [
            ("id1", "inv1", "stark1", "ext1", 9500, "created",
             datetime.now(UTC).isoformat(),
             datetime.now(UTC).isoformat(),
             None, 0, None, None),
            ("id2", "inv2", "stark2", "ext2", 8500, "processing",
             datetime.now(UTC).isoformat(),
             datetime.now(UTC).isoformat(),
             None, 0, None, None),
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

    def test_list_transfers_with_status_filter(self, repository, mock_db):
        """Test listing transfers with status filter."""
        mock_rows = [
            ("id1", "inv1", "stark1", "ext1", 9500, "success",
             datetime.now(UTC).isoformat(),
             datetime.now(UTC).isoformat(),
             datetime.now(UTC).isoformat(), 0, None, None),
        ]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.list(status="success", limit=10, offset=0)

        assert len(result) == 1
        assert result[0].status == TransferStatus.SUCCESS

        # Verify query includes status filter
        call_args = mock_conn.execute.call_args
        query = call_args[0][0]
        assert "WHERE status = ?" in query

    def test_count_transfers(self, repository, mock_db):
        """Test counting transfers."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (25,)
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.count()

        assert result == 25

    def test_count_transfers_with_status(self, repository, mock_db):
        """Test counting transfers with status filter."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (10,)
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.count(status="success")

        assert result == 10

    def test_list_by_status(self, repository, mock_db):
        """Test listing transfers by status."""
        mock_rows = [
            ("id1", "inv1", None, "ext1", 9500, "pending",
             datetime.now(UTC).isoformat(),
             datetime.now(UTC).isoformat(),
             None, 0, None, None),
        ]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.list_by_status(TransferStatus.PENDING)

        assert len(result) == 1
        assert result[0].status == TransferStatus.PENDING

    def test_row_to_model_conversion(self, repository):
        """Test database row to model conversion."""
        now = datetime.now(UTC).isoformat()
        row = (
            "transfer-id",
            "invoice-id",
            "stark-id",
            "external-id",
            9500,
            "success",
            now,
            now,
            now,
            2,  # retry_count
            now,
            None,  # error_message
        )

        result = repository._row_to_model(row)

        assert isinstance(result, TransferModel)
        assert result.id == "transfer-id"
        assert result.invoice_id == "invoice-id"
        assert result.stark_transfer_id == "stark-id"
        assert result.external_id == "external-id"
        assert result.amount == 9500
        assert result.status == TransferStatus.SUCCESS
        assert result.retry_count == 2

    def test_create_with_all_fields(self, repository, mock_db):
        """Test creating transfer with all fields populated."""
        now = datetime.now(UTC)
        transfer = TransferModel(
            id="full-transfer",
            invoice_id="invoice-123",
            stark_transfer_id="stark-456",
            external_id="ext-789",
            amount=10000,
            status=TransferStatus.SUCCESS,
            created_at=now,
            updated_at=now,
            completed_at=now,
            retry_count=1,
            last_retry_at=now,
            error_message=None,
        )

        mock_conn = MagicMock()
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        repository.create(transfer)

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        params = call_args[0][1]

        assert params[0] == "full-transfer"
        assert params[1] == "invoice-123"
        assert params[2] == "stark-456"
        assert params[3] == "ext-789"
        assert params[4] == 10000
        assert params[5] == "success"

    def test_list_empty_result(self, repository, mock_db):
        """Test listing transfers with no results."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.list()

        assert result == []
        assert len(result) == 0

    def test_count_empty_result(self, repository, mock_db):
        """Test counting transfers with no results."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.execute.return_value = mock_cursor
        mock_db.get_db.return_value.__enter__.return_value = mock_conn

        result = repository.count()

        assert result == 0
