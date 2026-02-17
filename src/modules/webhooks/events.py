"""
Webhook Events.

This module contains event payload definitions for webhook-related events
used with the EventBus system.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.shared.events.types import EventType

# Event type constants for webhooks
INVOICE_PAID = EventType.INVOICE_PAID
TRANSFER_PROCESSING = EventType.TRANSFER_PROCESSING
TRANSFER_COMPLETED = EventType.TRANSFER_COMPLETED
TRANSFER_FAILED = EventType.TRANSFER_FAILED
WEBHOOK_VALIDATION_FAILED = EventType.WEBHOOK_VALIDATION_FAILED


@dataclass
class InvoicePaidEventPayload:
    """
    Payload for invoice paid event.

    Published when a webhook confirms an invoice has been paid.
    Contains all payment details including fees and net amount.
    """

    invoice_id: str
    stark_invoice_id: str
    amount: float
    fee: float
    net_amount: float
    customer_tax_id: str
    paid_at: datetime

    def to_dict(self) -> dict[str, Any]:
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


@dataclass
class TransferProcessingEventPayload:
    """
    Payload for transfer processing event.

    Published when a transfer webhook indicates the transfer
    is being processed by the bank.
    """

    transfer_id: str
    stark_transfer_id: str
    invoice_id: str | None
    amount: float
    external_id: str
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "transfer_id": self.transfer_id,
            "stark_transfer_id": self.stark_transfer_id,
            "invoice_id": self.invoice_id,
            "amount": self.amount,
            "external_id": self.external_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class TransferCompletedEventPayload:
    """
    Payload for transfer completed event.

    Published when a transfer webhook confirms successful completion.
    """

    transfer_id: str
    stark_transfer_id: str
    invoice_id: str | None
    amount: float
    fee: float | None
    external_id: str
    completed_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "transfer_id": self.transfer_id,
            "stark_transfer_id": self.stark_transfer_id,
            "invoice_id": self.invoice_id,
            "amount": self.amount,
            "fee": self.fee,
            "external_id": self.external_id,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


@dataclass
class TransferFailedEventPayload:
    """
    Payload for transfer failed event.

    Published when a transfer webhook indicates failure.
    Contains error details for debugging and logging.
    """

    transfer_id: str
    stark_transfer_id: str
    invoice_id: str | None
    amount: float
    external_id: str
    error_code: str | None
    error_message: str | None
    failed_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "transfer_id": self.transfer_id,
            "stark_transfer_id": self.stark_transfer_id,
            "invoice_id": self.invoice_id,
            "amount": self.amount,
            "external_id": self.external_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
        }


@dataclass
class WebhookValidationFailedEventPayload:
    """
    Payload for webhook validation failed event.

    Published when a webhook signature validation fails,
    indicating potential security issues or malformed requests.
    """

    webhook_type: str  # "invoice" or "transfer"
    source_ip: str | None
    error_message: str
    timestamp: datetime
    raw_payload_preview: str | None = None  # First N chars for debugging

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for event payload."""
        return {
            "webhook_type": self.webhook_type,
            "source_ip": self.source_ip,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "raw_payload_preview": self.raw_payload_preview,
        }
