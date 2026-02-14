import json
from datetime import datetime
from typing import List, Optional

from src.shared.database.base_repository import BaseRepository
from src.shared.events.types import Event, EventType
from src.shared.utils.logger import get_logger

logger = get_logger("shared.events.event_logger")

class EventLogger(BaseRepository):
    def log_event(self, event: Event) -> None:
        """Persists an event to the events_log table."""
        try:
            query = """
                INSERT INTO events_log
                (event_id, event_type, payload, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """

            payload_json = json.dumps(event.payload, default=str)
            metadata_json = (
                json.dumps(event.metadata, default=str) if event.metadata else None
            )

            self._execute(query, (
                event.event_id,
                event.event_type.value,
                payload_json,
                metadata_json,
                event.timestamp.isoformat()
            ))
            logger.debug(f"Event {event.event_id} persisted to database")
        except Exception as e:
            logger.error(f"Failed to persist event {event.event_id}: {str(e)}")

    def get_events(
        self, event_type: Optional[str] = None, limit: int = 100
    ) -> List[Event]:
        """Retrieves events from the events_log table."""
        try:
            query = "SELECT * FROM events_log"
            params = []

            if event_type:
                query += " WHERE event_type = ?"
                params.append(event_type)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = self._fetchall(query, tuple(params))

            events = []
            for row in rows:
                event = Event(
                    event_id=row['event_id'],
                    event_type=EventType(row['event_type']),
                    payload=json.loads(row['payload']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else None,
                    timestamp=datetime.fromisoformat(row['timestamp'])
                )
                events.append(event)
            return events
        except Exception as e:
            logger.error(f"Failed to fetch events: {str(e)}")
            return []

def event_logger_handler(event: Event) -> None:
    repository = EventLogger()
    repository.log_event(event)
