"""
Invoice Models.

This module contains the data models for the invoice domain,
including the InvoiceModel dataclass and InvoiceStatus enum.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class InvoiceStatus(str, Enum):
    """Invoice status enumeration."""
    PENDING = "pending"
    CREATED = "created"
    PAID = "paid"
    CANCELED = "canceled"
    OVERDUE = "overdue"
    EXPIRED = "expired"
    FAILED = "failed"


@dataclass
class InvoiceModel:
    """
    Represents an invoice in the system.

    This dataclass holds all invoice information including customer details,
    amounts, status, and retry tracking for failed operations.
    """
    # Required fields
    amount: float
    customer_name: str
    customer_tax_id: str
    customer_email: str

    # Auto-generated fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: InvoiceStatus = InvoiceStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Stark Bank fields (populated after creation)
    stark_invoice_id: Optional[str] = None
    due_date: Optional[datetime] = None

    # Payment fields (populated when paid)
    paid_at: Optional[datetime] = None
    fee: Optional[float] = None
    net_amount: Optional[float] = None

    # Retry tracking
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate fields after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate invoice fields."""
        if self.amount <= 0:
            raise ValueError("Amount must be positive")

        if not self.customer_name or not self.customer_name.strip():
            raise ValueError("Customer name is required")

        if not self.customer_tax_id or not self.customer_tax_id.strip():
            raise ValueError("Customer tax ID is required")

        if not self.customer_email or not self.customer_email.strip():
            raise ValueError("Customer email is required")

        # Ensure status is InvoiceStatus enum
        if isinstance(self.status, str):
            self.status = InvoiceStatus(self.status)

    def calculate_net_amount(self) -> Optional[float]:
        """
        Calculate net amount after fee deduction.

        Returns:
            Net amount if fee is set, otherwise None
        """
        if self.fee is not None:
            self.net_amount = self.amount - self.fee
            return self.net_amount
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert invoice to dictionary representation.

        Returns:
            Dictionary with all invoice fields
        """
        return {
            "id": self.id,
            "stark_invoice_id": self.stark_invoice_id,
            "amount": self.amount,
            "customer_name": self.customer_name,
            "customer_tax_id": self.customer_tax_id,
            "customer_email": self.customer_email,
            "status": (
                self.status.value
                if isinstance(self.status, InvoiceStatus)
                else self.status
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "fee": self.fee,
            "net_amount": self.net_amount,
            "retry_count": self.retry_count,
            "last_retry_at": (
                self.last_retry_at.isoformat() if self.last_retry_at else None
            ),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvoiceModel":
        """
        Create an InvoiceModel from a dictionary.

        Args:
            data: Dictionary with invoice fields

        Returns:
            InvoiceModel instance
        """
        # Parse datetime fields
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif not created_at:
            created_at = datetime.now(timezone.utc)

        due_date = data.get("due_date")
        if due_date and isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date)

        paid_at = data.get("paid_at")
        if paid_at and isinstance(paid_at, str):
            paid_at = datetime.fromisoformat(paid_at)

        last_retry_at = data.get("last_retry_at")
        if last_retry_at and isinstance(last_retry_at, str):
            last_retry_at = datetime.fromisoformat(last_retry_at)

        # Parse status
        status = data.get("status", InvoiceStatus.PENDING)
        if isinstance(status, str):
            status = InvoiceStatus(status)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            stark_invoice_id=data.get("stark_invoice_id"),
            amount=data["amount"],
            customer_name=data["customer_name"],
            customer_tax_id=data["customer_tax_id"],
            customer_email=data["customer_email"],
            status=status,
            created_at=created_at,
            due_date=due_date,
            paid_at=paid_at,
            fee=data.get("fee"),
            net_amount=data.get("net_amount"),
            retry_count=data.get("retry_count", 0),
            last_retry_at=last_retry_at,
            error_message=data.get("error_message"),
        )

    def mark_as_created(self, stark_invoice_id: str) -> None:
        """Mark invoice as successfully created in Stark Bank."""
        self.stark_invoice_id = stark_invoice_id
        self.status = InvoiceStatus.CREATED
        self.error_message = None

    def mark_as_paid(self, fee: float, paid_at: datetime = None) -> None:
        """Mark invoice as paid."""
        self.status = InvoiceStatus.PAID
        self.fee = fee
        self.paid_at = paid_at or datetime.now(timezone.utc)
        self.calculate_net_amount()

    def mark_as_failed(self, error_message: str) -> None:
        """Mark invoice as failed."""
        self.status = InvoiceStatus.FAILED
        self.error_message = error_message
        self.retry_count += 1
        self.last_retry_at = datetime.now(timezone.utc)
