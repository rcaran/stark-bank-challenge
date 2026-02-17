"""
Webhook Models.

This module contains the data models for webhook processing,
including base webhook event structure and specific payload parsers
for invoice and transfer webhooks from Stark Bank.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class WebhookEventType(StrEnum):
    """Webhook event types from Stark Bank."""
    # Invoice events
    INVOICE_CREATED = "created"
    INVOICE_CREDITED = "credited"
    INVOICE_CANCELED = "canceled"
    INVOICE_EXPIRED = "expired"

    # Transfer events
    TRANSFER_CREATED = "created"
    TRANSFER_PROCESSING = "processing"
    TRANSFER_SUCCESS = "success"
    TRANSFER_FAILED = "failed"


@dataclass
class WebhookEvent:
    """
    Base structure for webhook events from Stark Bank.

    This represents the outer structure of a webhook payload
    containing the event log information.
    """
    subscription: str
    event_id: str
    event_type: str
    log_id: str
    log_created: datetime
    raw_payload: dict[str, Any] = field(default_factory=dict)
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebhookEvent:
        """
        Parse webhook event from raw payload dictionary.

        Args:
            data: Raw webhook payload from Stark Bank

        Returns:
            Parsed WebhookEvent instance

        Raises:
            ValueError: If required fields are missing
        """
        if "event" not in data:
            raise ValueError("Missing 'event' field in webhook payload")

        event = data["event"]

        if "log" not in event:
            raise ValueError("Missing 'log' field in webhook event")

        log = event["log"]

        # Parse log created timestamp
        log_created = log.get("created")
        if isinstance(log_created, str):
            log_created = datetime.fromisoformat(log_created)
        elif log_created is None:
            log_created = datetime.now(UTC)

        return cls(
            subscription=event.get("subscription", ""),
            event_id=str(event.get("id", "")),
            event_type=log.get("type", ""),
            log_id=str(log.get("id", "")),
            log_created=log_created,
            raw_payload=data,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "subscription": self.subscription,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "log_id": self.log_id,
            "log_created": self.log_created.isoformat() if self.log_created else None,
            "received_at": self.received_at.isoformat() if self.received_at else None,
        }


@dataclass
class InvoiceWebhookPayload:
    """
    Parser for invoice webhook payload from Stark Bank.

    Extracts invoice-specific information from the webhook event,
    including payment details when an invoice is paid.
    """
    invoice_id: str
    status: str
    amount: int  # In centavos
    fee: int | None = None  # In centavos
    name: str | None = None
    tax_id: str | None = None
    created: datetime | None = None
    updated: datetime | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def amount_decimal(self) -> float:
        """Get amount in decimal format (reais)."""
        return self.amount / 100.0

    @property
    def fee_decimal(self) -> float | None:
        """Get fee in decimal format (reais)."""
        return self.fee / 100.0 if self.fee is not None else None

    @property
    def net_amount(self) -> int | None:
        """Calculate net amount (amount - fee) in centavos."""
        if self.fee is not None:
            return self.amount - self.fee
        return None

    @property
    def net_amount_decimal(self) -> float | None:
        """Calculate net amount in decimal format (reais)."""
        net = self.net_amount
        return net / 100.0 if net is not None else None

    @classmethod
    def from_webhook_event(cls, webhook: WebhookEvent) -> InvoiceWebhookPayload:
        """
        Extract invoice payload from webhook event.

        Args:
            webhook: Parsed WebhookEvent instance

        Returns:
            Parsed InvoiceWebhookPayload instance

        Raises:
            ValueError: If invoice data is missing or invalid
        """
        raw = webhook.raw_payload

        if "event" not in raw or "log" not in raw["event"]:
            raise ValueError("Invalid webhook structure")

        log = raw["event"]["log"]
        invoice = log.get("invoice", {})

        if not invoice:
            raise ValueError("Missing invoice data in webhook payload")

        # Parse timestamp fields
        created = invoice.get("created")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)

        updated = invoice.get("updated")
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)

        return cls(
            invoice_id=str(invoice.get("id", "")),
            status=webhook.event_type,  # Use event type instead of invoice status
            amount=int(invoice.get("amount", 0)),
            fee=int(invoice.get("fee")) if invoice.get("fee") is not None else None,
            name=invoice.get("name"),
            tax_id=invoice.get("taxId"),
            created=created,
            updated=updated,
            raw_data=invoice,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InvoiceWebhookPayload:
        """
        Create payload from dictionary (convenience method).

        Args:
            data: Raw webhook payload dictionary

        Returns:
            Parsed InvoiceWebhookPayload instance
        """
        webhook = WebhookEvent.from_dict(data)
        return cls.from_webhook_event(webhook)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "invoice_id": self.invoice_id,
            "status": self.status,
            "amount": self.amount,
            "amount_decimal": self.amount_decimal,
            "fee": self.fee,
            "fee_decimal": self.fee_decimal,
            "net_amount": self.net_amount,
            "net_amount_decimal": self.net_amount_decimal,
            "name": self.name,
            "tax_id": self.tax_id,
            "created": self.created.isoformat() if self.created else None,
            "updated": self.updated.isoformat() if self.updated else None,
        }


@dataclass
class TransferWebhookPayload:
    """
    Parser for transfer webhook payload from Stark Bank.

    Extracts transfer-specific information from the webhook event,
    including status updates and error information.
    """
    transfer_id: str
    status: str
    amount: int  # In centavos
    external_id: str | None = None
    bank_code: str | None = None
    branch_code: str | None = None
    account_number: str | None = None
    account_type: str | None = None
    name: str | None = None
    tax_id: str | None = None
    fee: int | None = None  # In centavos
    created: datetime | None = None
    updated: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def amount_decimal(self) -> float:
        """Get amount in decimal format (reais)."""
        return self.amount / 100.0

    @property
    def fee_decimal(self) -> float | None:
        """Get fee in decimal format (reais)."""
        return self.fee / 100.0 if self.fee is not None else None

    @property
    def is_successful(self) -> bool:
        """Check if transfer completed successfully."""
        return self.status == "success"

    @property
    def is_failed(self) -> bool:
        """Check if transfer failed."""
        return self.status == "failed"

    @property
    def is_processing(self) -> bool:
        """Check if transfer is still processing."""
        return self.status == "processing"

    @classmethod
    def from_webhook_event(cls, webhook: WebhookEvent) -> TransferWebhookPayload:
        """
        Extract transfer payload from webhook event.

        Args:
            webhook: Parsed WebhookEvent instance

        Returns:
            Parsed TransferWebhookPayload instance

        Raises:
            ValueError: If transfer data is missing or invalid
        """
        raw = webhook.raw_payload

        if "event" not in raw or "log" not in raw["event"]:
            raise ValueError("Invalid webhook structure")

        log = raw["event"]["log"]
        transfer = log.get("transfer", {})

        if not transfer:
            raise ValueError("Missing transfer data in webhook payload")

        # Parse timestamp fields
        created = transfer.get("created")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)

        updated = transfer.get("updated")
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)

        # Extract error information from log if present
        errors = log.get("errors", [])
        error_code = None
        error_message = None
        if errors:
            error_code = errors[0].get("code")
            error_message = errors[0].get("message")

        return cls(
            transfer_id=str(transfer.get("id", "")),
            status=webhook.event_type,  # Use event type instead of transfer status
            amount=int(transfer.get("amount", 0)),
            external_id=transfer.get("externalId"),
            bank_code=transfer.get("bankCode"),
            branch_code=transfer.get("branchCode"),
            account_number=transfer.get("accountNumber"),
            account_type=transfer.get("accountType"),
            name=transfer.get("name"),
            tax_id=transfer.get("taxId"),
            fee=int(transfer.get("fee")) if transfer.get("fee") is not None else None,
            created=created,
            updated=updated,
            error_code=error_code,
            error_message=error_message,
            raw_data=transfer,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransferWebhookPayload:
        """
        Create payload from dictionary (convenience method).

        Args:
            data: Raw webhook payload dictionary

        Returns:
            Parsed TransferWebhookPayload instance
        """
        webhook = WebhookEvent.from_dict(data)
        return cls.from_webhook_event(webhook)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "transfer_id": self.transfer_id,
            "status": self.status,
            "amount": self.amount,
            "amount_decimal": self.amount_decimal,
            "external_id": self.external_id,
            "bank_code": self.bank_code,
            "branch_code": self.branch_code,
            "account_number": self.account_number,
            "account_type": self.account_type,
            "name": self.name,
            "tax_id": self.tax_id,
            "fee": self.fee,
            "fee_decimal": self.fee_decimal,
            "created": self.created.isoformat() if self.created else None,
            "updated": self.updated.isoformat() if self.updated else None,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "is_successful": self.is_successful,
            "is_failed": self.is_failed,
            "is_processing": self.is_processing,
        }
