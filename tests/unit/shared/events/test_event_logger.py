from unittest.mock import MagicMock
from src.shared.events.logger import EventLogger
from src.shared.events.types import Event, EventType

def test_log_event(mocker):
    # Mock DatabaseConnection
    mock_db = mocker.patch("src.shared.database.base_repository.DatabaseConnection")
    mock_conn = MagicMock()
    mock_db.return_value.get_db.return_value.__enter__.return_value = mock_conn
    
    logger = EventLogger()
    event = Event(event_type=EventType.INVOICE_CREATED, payload={"id": 123}, metadata={"source": "test"})
    
    logger.log_event(event)

    # Check if execute was called
    args, _ = mock_conn.execute.call_args
    query = args[0]
    params = args[1]
    
    assert "INSERT INTO events_log" in query
    assert params[0] == event.event_id
    assert params[1] == "invoice.created"
    assert '"id": 123' in params[2]
