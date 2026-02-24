from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.shared.events.logger import EventLogger
from src.shared.events.types import Event, EventType


def test_log_event(mocker):
    # Mock DatabaseConnection
    mock_db = mocker.patch("src.shared.database.base_repository.DatabaseConnection")
    mock_conn = MagicMock()
    mock_db.return_value.get_db.return_value.__enter__.return_value = mock_conn

    logger = EventLogger()
    event = Event(
        event_type=EventType.INVOICE_CREATED,
        payload={"id": 123},
        metadata={"source": "test"},
    )

    logger.log_event(event)

    # Check if execute was called
    args, _ = mock_conn.execute.call_args
    query = args[0]
    params = args[1]

    assert "INSERT INTO events_log" in query
    assert params[0] == event.event_id
    assert params[1] == "invoice.created"
    assert '"id": 123' in params[2]


class TestGetEvents:
    """Tests for EventLogger.get_events() with the new filter parameters."""

    def _make_mock_row(self, event_type="invoice.paid"):
        row = MagicMock()
        row.__getitem__ = lambda self, key: {
            "event_id": "evt-1",
            "event_type": event_type,
            "payload": '{"amount": 100}',
            "metadata": None,
            "timestamp": "2026-01-01T10:00:00",
        }[key]
        return row

    def test_get_events_no_filters(self, mocker):
        """Returns events with no WHERE clause when no filters supplied."""
        mock_db = mocker.patch("src.shared.database.base_repository.DatabaseConnection")
        mock_conn = MagicMock()
        mock_db.return_value.get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        el = EventLogger()
        result = el.get_events()

        args, _ = mock_conn.execute.call_args
        query = args[0]
        params = args[1]

        assert "WHERE" not in query
        assert "ORDER BY timestamp DESC LIMIT ? OFFSET ?" in query
        assert params == (100, 0)
        assert result == []

    def test_get_events_with_event_type(self, mocker):
        """Adds WHERE event_type = ? when event_type filter is provided."""
        mock_db = mocker.patch("src.shared.database.base_repository.DatabaseConnection")
        mock_conn = MagicMock()
        mock_db.return_value.get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        el = EventLogger()
        el.get_events(event_type="invoice.paid")

        args, _ = mock_conn.execute.call_args
        query, params = args[0], args[1]

        assert "WHERE event_type = ?" in query
        assert "invoice.paid" in params

    def test_get_events_with_date_range(self, mocker):
        """Adds timestamp conditions when start_date and end_date are supplied."""
        mock_db = mocker.patch("src.shared.database.base_repository.DatabaseConnection")
        mock_conn = MagicMock()
        mock_db.return_value.get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        el = EventLogger()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 1, 31, tzinfo=UTC)
        el.get_events(start_date=start, end_date=end)

        args, _ = mock_conn.execute.call_args
        query, params = args[0], args[1]

        assert "timestamp >= ?" in query
        assert "timestamp <= ?" in query
        assert start.isoformat() in params
        assert end.isoformat() in params

    def test_get_events_with_all_filters(self, mocker):
        """All filters combined produce AND-joined WHERE clause."""
        mock_db = mocker.patch("src.shared.database.base_repository.DatabaseConnection")
        mock_conn = MagicMock()
        mock_db.return_value.get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        el = EventLogger()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 1, 31, tzinfo=UTC)
        el.get_events(event_type="transfer.completed", start_date=start, end_date=end, limit=10, offset=20)

        args, _ = mock_conn.execute.call_args
        query, params = args[0], args[1]

        assert "event_type = ?" in query
        assert "timestamp >= ?" in query
        assert "timestamp <= ?" in query
        assert params[-2] == 10   # limit
        assert params[-1] == 20  # offset

    def test_get_events_returns_empty_on_exception(self, mocker):
        """Returns empty list when the database raises an exception."""
        mock_db = mocker.patch("src.shared.database.base_repository.DatabaseConnection")
        mock_db.return_value.get_db.side_effect = Exception("db error")

        el = EventLogger()
        result = el.get_events()

        assert result == []


class TestCountEvents:
    """Tests for EventLogger.count_events()."""

    def test_count_events_no_filters(self, mocker):
        """COUNT query has no WHERE clause when no filters are supplied."""
        mock_db = mocker.patch("src.shared.database.base_repository.DatabaseConnection")
        mock_conn = MagicMock()
        mock_db.return_value.get_db.return_value.__enter__.return_value = mock_conn
        row = MagicMock()
        row.__getitem__ = lambda self, key: {"total": 42}[key]
        mock_conn.execute.return_value.fetchone.return_value = row

        el = EventLogger()
        result = el.count_events()

        args, _ = mock_conn.execute.call_args
        query = args[0]

        assert "SELECT COUNT(*)" in query
        assert "WHERE" not in query
        assert result == 42

    def test_count_events_with_event_type(self, mocker):
        """Adds WHERE event_type = ? filter."""
        mock_db = mocker.patch("src.shared.database.base_repository.DatabaseConnection")
        mock_conn = MagicMock()
        mock_db.return_value.get_db.return_value.__enter__.return_value = mock_conn
        row = MagicMock()
        row.__getitem__ = lambda self, key: {"total": 7}[key]
        mock_conn.execute.return_value.fetchone.return_value = row

        el = EventLogger()
        result = el.count_events(event_type="invoice.paid")

        args, _ = mock_conn.execute.call_args
        query, params = args[0], args[1]

        assert "event_type = ?" in query
        assert "invoice.paid" in params
        assert result == 7

    def test_count_events_returns_zero_on_exception(self, mocker):
        """Returns 0 when the database raises an exception."""
        mock_db = mocker.patch("src.shared.database.base_repository.DatabaseConnection")
        mock_db.return_value.get_db.side_effect = Exception("db error")

        el = EventLogger()
        result = el.count_events()

        assert result == 0
