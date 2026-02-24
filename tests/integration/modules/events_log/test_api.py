"""Integration tests for Events Log API endpoints."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.events_log.api import events_log_router, get_event_log_service
from src.modules.events_log.models import EventLogListResponse, EventLogResponse
from src.modules.events_log.service import EventLogService
from src.shared.security.api_key import get_api_key_header

# Isolated test app
app = FastAPI()
app.include_router(events_log_router)

API_KEY = "test-api-key-12345"


def _make_response_item(**kwargs) -> EventLogResponse:
    """Build a minimal EventLogResponse."""
    defaults = {
        "id": 1,
        "event_id": "evt-abc",
        "event_type": "invoice.paid",
        "payload": {"amount": 5000},
        "metadata": None,
        "timestamp": datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
        "processed": False,
    }
    defaults.update(kwargs)
    return EventLogResponse(**defaults)


def _make_list_response(items=None, total=None, limit=50, offset=0) -> EventLogListResponse:
    if items is None:
        items = [_make_response_item()]
    return EventLogListResponse(
        items=items,
        total=total if total is not None else len(items),
        limit=limit,
        offset=offset,
    )


@pytest.fixture
def mock_service():
    """Create mock EventLogService."""
    return Mock(spec=EventLogService)


@pytest.fixture
def mock_api_key():
    def override():
        return API_KEY
    return override


@pytest.fixture
def client(mock_service, mock_api_key):
    """Test client with mocked service and auth."""
    app.dependency_overrides[get_event_log_service] = lambda: mock_service
    app.dependency_overrides[get_api_key_header] = mock_api_key
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth(mock_service):
    """Test client without auth override (for auth failure tests)."""
    app.dependency_overrides[get_event_log_service] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetEventLogsEndpoint:
    """Tests for GET /events-log."""

    def test_returns_200_with_results(self, client, mock_service):
        """Returns 200 and valid response body when events exist."""
        mock_service.list_events.return_value = _make_list_response()

        response = client.get("/events-log", headers={"X-API-Key": API_KEY})

        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert len(body["items"]) == 1
        assert body["items"][0]["event_type"] == "invoice.paid"

    def test_returns_empty_list_when_no_events(self, client, mock_service):
        """Returns 200 with empty items when there are no events."""
        mock_service.list_events.return_value = _make_list_response(items=[], total=0)

        response = client.get("/events-log", headers={"X-API-Key": API_KEY})

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_event_type_filter_passed_to_service(self, client, mock_service):
        """event_type query param is forwarded to service.list_events()."""
        mock_service.list_events.return_value = _make_list_response()

        client.get("/events-log?event_type=invoice.paid", headers={"X-API-Key": API_KEY})

        call_kwargs = mock_service.list_events.call_args.kwargs
        assert call_kwargs["event_type"] == "invoice.paid"

    def test_transfer_event_type_filter(self, client, mock_service):
        """Works with transfer event types too."""
        mock_service.list_events.return_value = _make_list_response(
            items=[_make_response_item(event_type="transfer.completed")], total=1
        )

        response = client.get(
            "/events-log?event_type=transfer.completed",
            headers={"X-API-Key": API_KEY},
        )

        assert response.status_code == 200
        call_kwargs = mock_service.list_events.call_args.kwargs
        assert call_kwargs["event_type"] == "transfer.completed"

    def test_date_range_filter_passed_to_service(self, client, mock_service):
        """start_date and end_date query params are forwarded to service."""
        mock_service.list_events.return_value = _make_list_response()

        client.get(
            "/events-log?start_date=2026-01-01T00:00:00Z&end_date=2026-01-31T23:59:59Z",
            headers={"X-API-Key": API_KEY},
        )

        call_kwargs = mock_service.list_events.call_args.kwargs
        assert call_kwargs["start_date"] is not None
        assert call_kwargs["end_date"] is not None

    def test_pagination_passed_to_service(self, client, mock_service):
        """limit and offset query params are forwarded to service."""
        mock_service.list_events.return_value = _make_list_response(limit=10, offset=20)

        client.get(
            "/events-log?limit=10&offset=20",
            headers={"X-API-Key": API_KEY},
        )

        call_kwargs = mock_service.list_events.call_args.kwargs
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 20

    def test_default_pagination_values(self, client, mock_service):
        """Default limit=50 and offset=0 are used when not specified."""
        mock_service.list_events.return_value = _make_list_response()

        client.get("/events-log", headers={"X-API-Key": API_KEY})

        call_kwargs = mock_service.list_events.call_args.kwargs
        assert call_kwargs["limit"] == 50
        assert call_kwargs["offset"] == 0

    def test_requires_api_key_returns_401(self, client_no_auth):
        """Returns 401 when no API key header is provided."""
        response = client_no_auth.get("/events-log")

        assert response.status_code == 401

    def test_invalid_event_type_returns_422(self, client):
        """Returns 422 when an unrecognised event_type is supplied."""
        response = client.get(
            "/events-log?event_type=not.a.real.type",
            headers={"X-API-Key": API_KEY},
        )

        assert response.status_code == 422

    def test_limit_below_minimum_returns_422(self, client):
        """Returns 422 when limit < 1."""
        response = client.get(
            "/events-log?limit=0",
            headers={"X-API-Key": API_KEY},
        )

        assert response.status_code == 422

    def test_limit_above_maximum_returns_422(self, client):
        """Returns 422 when limit > 500."""
        response = client.get(
            "/events-log?limit=501",
            headers={"X-API-Key": API_KEY},
        )

        assert response.status_code == 422

    def test_negative_offset_returns_422(self, client):
        """Returns 422 when offset is negative."""
        response = client.get(
            "/events-log?offset=-1",
            headers={"X-API-Key": API_KEY},
        )

        assert response.status_code == 422

    def test_response_contains_all_item_fields(self, client, mock_service):
        """Response items contain all expected EventLogResponse fields."""
        item = _make_response_item(
            id=7,
            event_id="evt-xyz",
            event_type="transfer.completed",
            payload={"amount": 9900},
            metadata={"source": "webhook"},
            timestamp=datetime(2026, 2, 1, 8, 30, 0, tzinfo=UTC),
            processed=True,
        )
        mock_service.list_events.return_value = _make_list_response(items=[item], total=1)

        response = client.get("/events-log", headers={"X-API-Key": API_KEY})

        assert response.status_code == 200
        item_data = response.json()["items"][0]
        assert item_data["id"] == 7
        assert item_data["event_id"] == "evt-xyz"
        assert item_data["event_type"] == "transfer.completed"
        assert item_data["payload"] == {"amount": 9900}
        assert item_data["metadata"] == {"source": "webhook"}
        assert item_data["processed"] is True
