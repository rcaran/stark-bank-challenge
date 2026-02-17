"""
Transfer Models.

This module contains the data models for the transfer domain,
including the TransferModel dataclass and TransferStatus enum.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class TransferStatus(StrEnum):
    """Transfer status enumeration."""

    PENDING = "pending"
    CREATED = "created"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TransferModel:
    """
    Represents a transfer in the system.

    This dataclass holds all transfer information including related invoice,
    amounts, status, and retry tracking for failed operations.
    """

    # Required fields
    invoice_id: str
    amount: float

    # Auto-generated fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    external_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TransferStatus = TransferStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Stark Bank fields (populated after creation)
    stark_transfer_id: str | None = None

    # Completion tracking
    completed_at: datetime | None = None

    # Retry tracking
    retry_count: int = 0
    last_retry_at: datetime | None = None
    error_message: str | None = None

    def __post_init__(self):
        """Validate fields after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate transfer fields."""
        if self.amount <= 0:
            raise ValueError("Amount must be positive")

        if not self.invoice_id or not self.invoice_id.strip():
            raise ValueError("Invoice ID is required")

        # Ensure status is TransferStatus enum
        if isinstance(self.status, str):
            self.status = TransferStatus(self.status)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert transfer to dictionary representation.

        Returns:
            Dictionary with all transfer fields
        """
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "stark_transfer_id": self.stark_transfer_id,
            "external_id": self.external_id,
            "amount": self.amount,
            "status": self.status.value,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "retry_count": self.retry_count,
            "last_retry_at": (
                self.last_retry_at.isoformat() if self.last_retry_at else None
            ),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransferModel:
        """
        Create TransferModel from dictionary.

        Args:
            data: Dictionary with transfer data

        Returns:
            TransferModel instance
        """
        # Parse datetime fields
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        updated_at = data.get("updated_at")
        if updated_at and isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        completed_at = data.get("completed_at")
        if completed_at and isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)

        last_retry_at = data.get("last_retry_at")
        if last_retry_at and isinstance(last_retry_at, str):
            last_retry_at = datetime.fromisoformat(last_retry_at)

        # Parse status
        status = data.get("status", TransferStatus.PENDING)
        if isinstance(status, str):
            status = TransferStatus(status)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            invoice_id=data["invoice_id"],
            stark_transfer_id=data.get("stark_transfer_id"),
            external_id=data.get("external_id", str(uuid.uuid4())),
            amount=float(data["amount"]),
            status=status,
            created_at=created_at or datetime.now(UTC),
            updated_at=updated_at or datetime.now(UTC),
            completed_at=completed_at,
            retry_count=data.get("retry_count", 0),
            last_retry_at=last_retry_at,
            error_message=data.get("error_message"),
        )

    def update_status(
        self, new_status: TransferStatus, error_message: str | None = None
    ) -> None:
        """
        Update transfer status and timestamp.

        Args:
            new_status: New status for the transfer
            error_message: Optional error message for failed transfers
        """
        self.status = new_status
        self.updated_at = datetime.now(UTC)

        if new_status == TransferStatus.SUCCESS:
            self.completed_at = datetime.now(UTC)
            self.error_message = None
        elif new_status == TransferStatus.FAILED:
            self.error_message = error_message

    def increment_retry(self) -> None:
        """Increment retry count and update last retry timestamp."""
        self.retry_count += 1
        self.last_retry_at = datetime.now(UTC)
