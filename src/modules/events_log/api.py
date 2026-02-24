"""
Events Log API Endpoints.

Provides a read-only endpoint to query the events_log table,
protected by API key authentication.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from src.modules.events_log.models import EventLogListResponse
from src.modules.events_log.repository import EventLogRepository
from src.modules.events_log.service import EventLogService
from src.shared.events.types import EventType
from src.shared.security.api_key import get_api_key_header
from src.shared.utils.logger import get_logger

logger = get_logger("modules.events_log.api")

events_log_router = APIRouter(
    prefix="/events-log",
    tags=["events-log"],
)

# Singleton service (same pattern as other modules)
_service: EventLogService | None = None


def get_event_log_service() -> EventLogService:
    """Get or create EventLogService instance."""
    global _service
    if _service is None:
        _service = EventLogService(repository=EventLogRepository())
    return _service


@events_log_router.get(
    "",
    response_model=EventLogListResponse,
    summary="List event logs",
    description=(
        "Returns a paginated list of all events recorded in the system. "
        "Supports filtering by event type and date range."
    ),
)
def list_event_logs(
    event_type: EventType | None = Query(
        None,
        description="Filter by event type (e.g. invoice.paid, transfer.completed)",
    ),
    start_date: datetime | None = Query(
        None,
        description="Include only events on or after this datetime (ISO 8601 UTC)",
    ),
    end_date: datetime | None = Query(
        None,
        description="Include only events on or before this datetime (ISO 8601 UTC)",
    ),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    _api_key: str = Depends(get_api_key_header),
    service: EventLogService = Depends(get_event_log_service),
) -> EventLogListResponse:
    """Query event logs with optional filters and pagination."""
    return service.list_events(
        event_type=event_type.value if event_type else None,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
