from unittest.mock import MagicMock
from src.shared.events.bus import EventBus
from src.shared.events.types import Event, EventType

def test_event_bus_singleton():
    bus1 = EventBus()
    bus2 = EventBus()
    assert bus1 is bus2

def test_subscribe_and_publish():
    bus = EventBus()
    # Reset subscribers for test
    bus._subscribers.clear()
    
    mock_handler = MagicMock()
    mock_handler.__name__ = "mock_handler"
    
    bus.subscribe(EventType.INVOICE_CREATED, mock_handler)
    
    event = Event(event_type=EventType.INVOICE_CREATED, payload={"id": 1})
    bus.publish(event)
    
    mock_handler.assert_called_once_with(event)

def test_no_handlers():
    bus = EventBus()
    bus._subscribers.clear()
    
    event = Event(event_type=EventType.INVOICE_PAID, payload={"id": 1})
    # Should not raise
    bus.publish(event)
