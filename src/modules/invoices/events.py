"""
Invoice Events.

This module contains event payload definitions for invoice-related events
used with the EventBus system.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

from src.shared.events.types import EventType

# Event type constants for invoices
INVOICE_CREATED = EventType.INVOICE_CREATED
INVOICE_CREATION_FAILED = EventType.INVOICE_CREATION_FAILED
INVOICE_PAID = EventType.INVOICE_PAID


@dataclass
class InvoiceCreatedEventPayload:
    """Payload for invoice created event."""
    invoice_id: str
    stark_invoice_id: str
    amount: float
    customer_name: str
    customer_tax_id: str
    customer_email: str
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "invoice_id": self.invoice_id,
            "stark_invoice_id": self.stark_invoice_id,
            "amount": self.amount,
            "customer_name": self.customer_name,
            "customer_tax_id": self.customer_tax_id,
            "customer_email": self.customer_email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class InvoiceCreationFailedEventPayload:
    """Payload for invoice creation failed event."""
    invoice_id: str
    amount: float
    customer_name: str
    customer_tax_id: str
    error_message: str
    retry_count: int
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "invoice_id": self.invoice_id,
            "amount": self.amount,
            "customer_name": self.customer_name,
            "customer_tax_id": self.customer_tax_id,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class InvoicePaidEventPayload:
    """Payload for invoice paid event."""
    invoice_id: str
    stark_invoice_id: str
    amount: float
    fee: float
    net_amount: float
    customer_tax_id: str
    paid_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "invoice_id": self.invoice_id,
            "stark_invoice_id": self.stark_invoice_id,
            "amount": self.amount,
            "fee": self.fee,
            "net_amount": self.net_amount,
            "customer_tax_id": self.customer_tax_id,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }
