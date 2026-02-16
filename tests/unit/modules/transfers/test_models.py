"""Unit tests for TransferModel."""

import uuid
from datetime import datetime, timezone

import pytest

from src.modules.transfers.models import TransferModel, TransferStatus


class TestTransferModel:
    """Tests for TransferModel dataclass."""

    def test_create_transfer_with_required_fields(self):
        """Test creating transfer with required fields."""
        invoice_id = str(uuid.uuid4())
        transfer = TransferModel(
            invoice_id=invoice_id,
            amount=10000,
        )

        assert transfer.invoice_id == invoice_id
        assert transfer.amount == 10000
        assert transfer.status == TransferStatus.PENDING
        assert transfer.id is not None
        assert transfer.external_id is not None
        assert transfer.created_at is not None
        assert transfer.updated_at is not None

    def test_create_transfer_with_all_fields(self):
        """Test creating transfer with all fields."""
        custom_id = str(uuid.uuid4())
        invoice_id = str(uuid.uuid4())
        external_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)

        transfer = TransferModel(
            id=custom_id,
            invoice_id=invoice_id,
            external_id=external_id,
            amount=50000,
            status=TransferStatus.CREATED,
            created_at=created_at,
            updated_at=updated_at,
            stark_transfer_id="stark-transfer-123",
        )

        assert transfer.id == custom_id
        assert transfer.invoice_id == invoice_id
        assert transfer.external_id == external_id
        assert transfer.amount == 50000
        assert transfer.status == TransferStatus.CREATED
        assert transfer.stark_transfer_id == "stark-transfer-123"

    def test_create_transfer_invalid_amount(self):
        """Test that negative amount raises ValueError."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            TransferModel(
                invoice_id=str(uuid.uuid4()),
                amount=-100,
            )

    def test_create_transfer_zero_amount(self):
        """Test that zero amount raises ValueError."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            TransferModel(
                invoice_id=str(uuid.uuid4()),
                amount=0,
            )

    def test_create_transfer_empty_invoice_id(self):
        """Test that empty invoice_id raises ValueError."""
        with pytest.raises(ValueError, match="Invoice ID is required"):
            TransferModel(
                invoice_id="",
                amount=1000,
            )

    def test_to_dict(self):
        """Test conversion to dictionary."""
        invoice_id = str(uuid.uuid4())
        transfer = TransferModel(
            invoice_id=invoice_id,
            amount=10000,
        )

        data = transfer.to_dict()

        assert data["id"] == transfer.id
        assert data["invoice_id"] == invoice_id
        assert data["amount"] == 10000
        assert data["status"] == "pending"
        assert data["external_id"] == transfer.external_id
        assert data["created_at"] is not None
        assert data["updated_at"] is not None
        assert data["completed_at"] is None
        assert data["retry_count"] == 0

    def test_from_dict_minimal(self):
        """Test creating transfer from dictionary with minimal fields."""
        invoice_id = str(uuid.uuid4())
        data = {
            "invoice_id": invoice_id,
            "amount": 10000,
        }

        transfer = TransferModel.from_dict(data)

        assert transfer.invoice_id == invoice_id
        assert transfer.amount == 10000
        assert transfer.status == TransferStatus.PENDING
        assert transfer.id is not None
        assert transfer.external_id is not None

    def test_from_dict_complete(self):
        """Test creating transfer from dictionary with all fields."""
        transfer_id = str(uuid.uuid4())
        invoice_id = str(uuid.uuid4())
        external_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        completed_at = datetime.now(timezone.utc)
        last_retry_at = datetime.now(timezone.utc)

        data = {
            "id": transfer_id,
            "invoice_id": invoice_id,
            "external_id": external_id,
            "stark_transfer_id": "stark-123",
            "amount": 50000,
            "status": "success",
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "retry_count": 2,
            "last_retry_at": last_retry_at.isoformat(),
            "error_message": "Test error",
        }

        transfer = TransferModel.from_dict(data)

        assert transfer.id == transfer_id
        assert transfer.invoice_id == invoice_id
        assert transfer.external_id == external_id
        assert transfer.stark_transfer_id == "stark-123"
        assert transfer.amount == 50000
        assert transfer.status == TransferStatus.SUCCESS
        assert transfer.retry_count == 2
        assert transfer.error_message == "Test error"

    def test_to_dict_from_dict_roundtrip(self):
        """Test that to_dict and from_dict are consistent."""
        invoice_id = str(uuid.uuid4())
        transfer = TransferModel(
            invoice_id=invoice_id,
            amount=10000,
            stark_transfer_id="stark-123",
        )

        data = transfer.to_dict()
        transfer2 = TransferModel.from_dict(data)

        assert transfer.id == transfer2.id
        assert transfer.invoice_id == transfer2.invoice_id
        assert transfer.amount == transfer2.amount
        assert transfer.status == transfer2.status
        assert transfer.stark_transfer_id == transfer2.stark_transfer_id

    def test_update_status_to_success(self):
        """Test updating status to SUCCESS."""
        transfer = TransferModel(
            invoice_id=str(uuid.uuid4()),
            amount=10000,
        )

        old_updated_at = transfer.updated_at
        transfer.update_status(TransferStatus.SUCCESS)

        assert transfer.status == TransferStatus.SUCCESS
        assert transfer.completed_at is not None
        assert transfer.error_message is None
        assert transfer.updated_at > old_updated_at

    def test_update_status_to_failed(self):
        """Test updating status to FAILED with error message."""
        transfer = TransferModel(
            invoice_id=str(uuid.uuid4()),
            amount=10000,
        )

        old_updated_at = transfer.updated_at
        error_msg = "Transfer failed due to insufficient funds"
        transfer.update_status(TransferStatus.FAILED, error_message=error_msg)

        assert transfer.status == TransferStatus.FAILED
        assert transfer.error_message == error_msg
        assert transfer.updated_at > old_updated_at

    def test_update_status_to_processing(self):
        """Test updating status to PROCESSING."""
        transfer = TransferModel(
            invoice_id=str(uuid.uuid4()),
            amount=10000,
        )

        old_updated_at = transfer.updated_at
        transfer.update_status(TransferStatus.PROCESSING)

        assert transfer.status == TransferStatus.PROCESSING
        assert transfer.updated_at > old_updated_at

    def test_increment_retry(self):
        """Test incrementing retry count."""
        transfer = TransferModel(
            invoice_id=str(uuid.uuid4()),
            amount=10000,
        )

        assert transfer.retry_count == 0
        assert transfer.last_retry_at is None

        transfer.increment_retry()

        assert transfer.retry_count == 1
        assert transfer.last_retry_at is not None

        old_retry_at = transfer.last_retry_at
        transfer.increment_retry()

        assert transfer.retry_count == 2
        assert transfer.last_retry_at > old_retry_at

    def test_status_transition_pending_to_created(self):
        """Test status transition from PENDING to CREATED."""
        transfer = TransferModel(
            invoice_id=str(uuid.uuid4()),
            amount=10000,
        )

        assert transfer.status == TransferStatus.PENDING
        transfer.update_status(TransferStatus.CREATED)
        assert transfer.status == TransferStatus.CREATED

    def test_status_transition_created_to_processing(self):
        """Test status transition from CREATED to PROCESSING."""
        transfer = TransferModel(
            invoice_id=str(uuid.uuid4()),
            amount=10000,
            status=TransferStatus.CREATED,
        )

        transfer.update_status(TransferStatus.PROCESSING)
        assert transfer.status == TransferStatus.PROCESSING

    def test_status_transition_processing_to_success(self):
        """Test status transition from PROCESSING to SUCCESS."""
        transfer = TransferModel(
            invoice_id=str(uuid.uuid4()),
            amount=10000,
            status=TransferStatus.PROCESSING,
        )

        transfer.update_status(TransferStatus.SUCCESS)
        assert transfer.status == TransferStatus.SUCCESS
        assert transfer.completed_at is not None

    def test_status_transition_processing_to_failed(self):
        """Test status transition from PROCESSING to FAILED."""
        transfer = TransferModel(
            invoice_id=str(uuid.uuid4()),
            amount=10000,
            status=TransferStatus.PROCESSING,
        )

        transfer.update_status(TransferStatus.FAILED, error_message="Network error")
        assert transfer.status == TransferStatus.FAILED
        assert transfer.error_message == "Network error"

    def test_status_enum_validation(self):
        """Test that invalid status string is validated."""
        with pytest.raises(ValueError):
            TransferModel(
                invoice_id=str(uuid.uuid4()),
                amount=10000,
                status="invalid_status",
            )

    def test_status_string_conversion(self):
        """Test that status string is converted to enum."""
        transfer = TransferModel.from_dict({
            "invoice_id": str(uuid.uuid4()),
            "amount": 10000,
            "status": "success",
        })

        assert isinstance(transfer.status, TransferStatus)
        assert transfer.status == TransferStatus.SUCCESS
