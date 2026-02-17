import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

"""Event type definitions and data structures."""

class EventType(StrEnum):
    # Invoice Events
    INVOICE_CREATED = "invoice.created"
    INVOICE_CREATION_FAILED = "invoice.creation_failed"
    INVOICE_PAID = "invoice.paid"

    # Transfer Events
    TRANSFER_CREATED = "transfer.created"
    TRANSFER_PROCESSING = "transfer.processing"
    TRANSFER_COMPLETED = "transfer.completed"
    TRANSFER_FAILED = "transfer.failed"

    # Webhook Events
    WEBHOOK_RECEIVED = "webhook.received"
    WEBHOOK_VALIDATION_FAILED = "webhook.validation_failed"

    # System Events
    SCHEDULER_TICK = "scheduler.tick"
    ERROR_OCCURRED = "system.error"


@dataclass
class Event:
    event_type: EventType
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] | None = None


EventHandler = Callable[[Event], None]
