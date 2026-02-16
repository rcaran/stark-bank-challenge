"""
Transfer Events.

This module contains event payload definitions for transfer-related events
used with the EventBus system.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from src.shared.events.types import EventType

# Event type constants for transfers
TRANSFER_INITIATED = EventType.TRANSFER_CREATED
TRANSFER_PROCESSING = EventType.TRANSFER_PROCESSING
TRANSFER_COMPLETED = EventType.TRANSFER_COMPLETED
TRANSFER_FAILED = EventType.TRANSFER_FAILED


@dataclass
class TransferInitiatedEventPayload:
    """Payload for transfer initiated event."""
    transfer_id: str
    invoice_id: str
    stark_transfer_id: str
    external_id: str
    amount: float
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "transfer_id": self.transfer_id,
            "invoice_id": self.invoice_id,
            "stark_transfer_id": self.stark_transfer_id,
            "external_id": self.external_id,
            "amount": self.amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class TransferProcessingEventPayload:
    """Payload for transfer processing event."""
    transfer_id: str
    invoice_id: str
    stark_transfer_id: str
    status: str
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "transfer_id": self.transfer_id,
            "invoice_id": self.invoice_id,
            "stark_transfer_id": self.stark_transfer_id,
            "status": self.status,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class TransferCompletedEventPayload:
    """Payload for transfer completed event."""
    transfer_id: str
    invoice_id: str
    stark_transfer_id: str
    amount: float
    completed_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "transfer_id": self.transfer_id,
            "invoice_id": self.invoice_id,
            "stark_transfer_id": self.stark_transfer_id,
            "amount": self.amount,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


@dataclass
class TransferFailedEventPayload:
    """Payload for transfer failed event."""
    transfer_id: str
    invoice_id: str
    stark_transfer_id: Optional[str]
    amount: float
    error_message: str
    retry_count: int
    failed_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "transfer_id": self.transfer_id,
            "invoice_id": self.invoice_id,
            "stark_transfer_id": self.stark_transfer_id,
            "amount": self.amount,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
        }
