"""Service layer for Events Log operations."""

from datetime import datetime

from src.modules.events_log.models import EventLogListResponse, EventLogResponse
from src.modules.events_log.repository import EventLogRepository
from src.shared.utils.logger import get_logger

logger = get_logger("modules.events_log.service")


class EventLogService:
    """Business logic for querying event logs."""

    def __init__(self, repository: EventLogRepository) -> None:
        self._repository = repository

    def list_events(
        self,
        event_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> EventLogListResponse:
        """
        Returns a paginated list of event log entries with optional filters.

        Args:
            event_type: Filter by EventType value (e.g. "invoice.paid")
            start_date: Include only events on or after this datetime (UTC)
            end_date:   Include only events on or before this datetime (UTC)
            limit:      Maximum number of results to return (default 50)
            offset:     Number of results to skip for pagination (default 0)

        Returns:
            EventLogListResponse with items, total, limit, and offset
        """
        logger.debug(
            "Listing event logs",
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        rows = self._repository.get_events(
            event_type=event_type,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
        )

        total = self._repository.count_events(
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
        )

        items = [EventLogResponse(**row) for row in rows]

        return EventLogListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def list_events_by_invoice_id(
        self,
        invoice_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> EventLogListResponse:
        """
        Returns all event log entries (invoices and transfers) related to
        a specific invoice_id, ordered from most recent to oldest.

        Args:
            invoice_id: The invoice UUID to filter by
            limit:      Maximum number of results to return (default 50)
            offset:     Number of results to skip for pagination (default 0)

        Returns:
            EventLogListResponse with items, total, limit, and offset
        """
        logger.debug(
            "Listing event logs by invoice_id",
            invoice_id=invoice_id,
            limit=limit,
            offset=offset,
        )

        rows = self._repository.get_events_by_invoice_id(
            invoice_id=invoice_id,
            limit=limit,
            offset=offset,
        )

        total = self._repository.count_events_by_invoice_id(invoice_id=invoice_id)

        items = [EventLogResponse(**row) for row in rows]

        return EventLogListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )
