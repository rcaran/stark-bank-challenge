"""Pydantic models for Events Log API responses."""

from datetime import datetime

from pydantic import BaseModel

from src.shared.events.types import EventType


class EventLogResponse(BaseModel):
    """Response model for a single event log entry."""

    id: int
    event_id: str
    event_type: str
    payload: dict
    metadata: dict | None
    timestamp: datetime
    processed: bool

    model_config = {"from_attributes": True}


class EventLogListResponse(BaseModel):
    """Response model for a paginated list of event log entries."""

    items: list[EventLogResponse]
    total: int
    limit: int
    offset: int
