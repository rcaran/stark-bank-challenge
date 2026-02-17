"""In-memory event bus for publish-subscribe messaging."""

from collections import defaultdict

from src.shared.events.types import Event, EventHandler, EventType
from src.shared.utils.logger import get_logger

logger = get_logger("shared.events.bus")


class EventBus:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = defaultdict(list)
        return cls._instance

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        handler_name = getattr(handler, "__name__", "unknown")
        logger.debug(f"Subscribing handler {handler_name} to {event_type}")
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        handler_name = getattr(handler, "__name__", "unknown")
        logger.debug(f"Unsubscribing handler {handler_name} from {event_type}")
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        logger.info(f"Publishing event {event.event_type} ({event.event_id})")

        handlers = self._subscribers.get(event.event_type, [])
        if not handlers:
            logger.debug(f"No handlers for event {event.event_type}")
            return

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    f"Error handling event {event.event_type} with {handler.__name__}",
                    error=str(e),
                    event_id=event.event_id,
                )
                # We catch exceptions to prevent one handler from blocking others
                # In a real system we might want a dead letter queue or retry mechanism


def get_event_bus() -> EventBus:
    return EventBus()
