import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional


class EventType(str, Enum):
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
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[Dict[str, Any]] = None

EventHandler = Callable[[Event], None]
