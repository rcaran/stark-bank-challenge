"""Repository for querying the events_log table."""

import json
from datetime import datetime

from src.shared.database.base_repository import BaseRepository
from src.shared.utils.logger import get_logger

logger = get_logger("modules.events_log.repository")


class EventLogRepository(BaseRepository):
    """Repository for reading events from the events_log table."""

    def get_events(
        self,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """
        Retrieves raw event rows from events_log with optional filters.

        Returns a list of dicts with keys:
            id, event_id, event_type, payload, metadata, timestamp, processed
        """
        try:
            query = "SELECT * FROM events_log"
            params: list = []
            conditions: list[str] = []

            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type)

            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date.isoformat())

            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date.isoformat())

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = self._fetchall(query, tuple(params))
            return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch event logs: {e!s}")
            return []

    def count_events(
        self,
        event_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Counts events in the events_log table with optional filters."""
        try:
            query = "SELECT COUNT(*) as total FROM events_log"
            params: list = []
            conditions: list[str] = []

            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type)

            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date.isoformat())

            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date.isoformat())

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            row = self._fetchone(query, tuple(params))
            return row["total"] if row else 0
        except Exception as e:
            logger.error(f"Failed to count event logs: {e!s}")
            return 0

    def get_events_by_invoice_id(
        self,
        invoice_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """
        Retrieves event rows whose payload contains the given invoice_id.

        Works for both invoice events (payload.invoice_id) and transfer
        events (payload.invoice_id), since every related event stores the
        invoice_id directly in its payload.
        """
        try:
            query = (
                "SELECT * FROM events_log "
                "WHERE json_extract(payload, '$.invoice_id') = ? "
                "ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            )
            rows = self._fetchall(query, (invoice_id, limit, offset))
            return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch event logs by invoice_id: {e!s}")
            return []

    def count_events_by_invoice_id(self, invoice_id: str) -> int:
        """Counts events whose payload contains the given invoice_id."""
        try:
            query = (
                "SELECT COUNT(*) as total FROM events_log "
                "WHERE json_extract(payload, '$.invoice_id') = ?"
            )
            row = self._fetchone(query, (invoice_id,))
            return row["total"] if row else 0
        except Exception as e:
            logger.error(f"Failed to count event logs by invoice_id: {e!s}")
            return 0

    @staticmethod
    def _row_to_dict(row) -> dict:
        """Converts a sqlite3.Row to a plain dict with parsed JSON fields."""
        return {
            "id": row["id"],
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "payload": json.loads(row["payload"]),
            "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
            "timestamp": row["timestamp"],
            "processed": bool(row["processed"]),
        }
