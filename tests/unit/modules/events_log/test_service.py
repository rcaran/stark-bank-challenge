"""Unit tests for EventLogService."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from src.modules.events_log.models import EventLogListResponse, EventLogResponse
from src.modules.events_log.service import EventLogService


def _make_row(**kwargs) -> dict:
    """Build a minimal event log row dict."""
    defaults = {
        "id": 1,
        "event_id": "evt-abc",
        "event_type": "invoice.paid",
        "payload": {"amount": 5000},
        "metadata": None,
        "timestamp": "2026-01-15T12:00:00",
        "processed": False,
    }
    defaults.update(kwargs)
    return defaults


class TestEventLogServiceListEvents:
    """Tests for EventLogService.list_events()."""

    @pytest.fixture
    def mock_repository(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_repository):
        return EventLogService(repository=mock_repository)

    def test_list_events_no_filters_returns_all(self, service, mock_repository):
        """Returns all events when no filters are provided."""
        rows = [_make_row(id=1), _make_row(id=2)]
        mock_repository.get_events.return_value = rows
        mock_repository.count_events.return_value = 2

        result = service.list_events()

        assert isinstance(result, EventLogListResponse)
        assert len(result.items) == 2
        assert result.total == 2
        assert result.limit == 50
        assert result.offset == 0

    def test_list_events_passes_event_type_filter(self, service, mock_repository):
        """Forwards event_type filter to repository."""
        mock_repository.get_events.return_value = []
        mock_repository.count_events.return_value = 0

        service.list_events(event_type="invoice.paid")

        mock_repository.get_events.assert_called_once_with(
            event_type="invoice.paid",
            limit=50,
            offset=0,
            start_date=None,
            end_date=None,
        )
        mock_repository.count_events.assert_called_once_with(
            event_type="invoice.paid",
            start_date=None,
            end_date=None,
        )

    def test_list_events_passes_date_range_filter(self, service, mock_repository):
        """Forwards start_date and end_date filters to repository."""
        mock_repository.get_events.return_value = []
        mock_repository.count_events.return_value = 0

        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 1, 31, tzinfo=UTC)

        service.list_events(start_date=start, end_date=end)

        mock_repository.get_events.assert_called_once_with(
            event_type=None,
            limit=50,
            offset=0,
            start_date=start,
            end_date=end,
        )

    def test_list_events_passes_pagination(self, service, mock_repository):
        """Forwards limit and offset to repository."""
        mock_repository.get_events.return_value = []
        mock_repository.count_events.return_value = 0

        service.list_events(limit=10, offset=30)

        mock_repository.get_events.assert_called_once_with(
            event_type=None,
            limit=10,
            offset=30,
            start_date=None,
            end_date=None,
        )

    def test_list_events_all_filters_combined(self, service, mock_repository):
        """All filters combined are forwarded correctly."""
        mock_repository.get_events.return_value = [_make_row()]
        mock_repository.count_events.return_value = 1

        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 1, 31, tzinfo=UTC)

        result = service.list_events(
            event_type="transfer.completed",
            start_date=start,
            end_date=end,
            limit=5,
            offset=10,
        )

        assert result.total == 1
        assert result.limit == 5
        assert result.offset == 10
        mock_repository.get_events.assert_called_once_with(
            event_type="transfer.completed",
            limit=5,
            offset=10,
            start_date=start,
            end_date=end,
        )

    def test_list_events_empty_result(self, service, mock_repository):
        """Returns empty items list and zero total when no events found."""
        mock_repository.get_events.return_value = []
        mock_repository.count_events.return_value = 0

        result = service.list_events(event_type="invoice.paid")

        assert result.items == []
        assert result.total == 0

    def test_list_events_response_item_fields(self, service, mock_repository):
        """Each item in the response has the expected fields."""
        row = _make_row(
            id=5,
            event_id="evt-xyz",
            event_type="transfer.completed",
            payload={"amount": 9900},
            metadata={"source": "webhook"},
            timestamp="2026-02-01T08:30:00",
            processed=True,
        )
        mock_repository.get_events.return_value = [row]
        mock_repository.count_events.return_value = 1

        result = service.list_events()
        item = result.items[0]

        assert isinstance(item, EventLogResponse)
        assert item.id == 5
        assert item.event_id == "evt-xyz"
        assert item.event_type == "transfer.completed"
        assert item.payload == {"amount": 9900}
        assert item.metadata == {"source": "webhook"}
        assert item.processed is True
