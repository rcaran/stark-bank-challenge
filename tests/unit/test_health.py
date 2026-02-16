"""
Unit tests for the health check module.

Tests health check functionality including database checks,
event bus checks, and overall health status.
"""

import time
from unittest.mock import MagicMock, patch

from src.health import (
    check_database,
    check_event_bus,
    check_health,
    get_uptime_seconds,
)


class TestDatabaseCheck:
    """Test suite for database health check."""

    @patch("src.health.DatabaseConnection")
    def test_database_check_success(self, mock_db_class):
        """Test that database check returns ok when database is accessible."""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [1]
        mock_conn.execute.return_value = mock_cursor

        mock_db = MagicMock()
        mock_db.connection = mock_conn
        mock_db_class.return_value = mock_db

        # Execute
        result = check_database()

        # Verify
        assert result["status"] == "ok"
        assert "message" in result
        assert "successful" in result["message"].lower()

        # Verify database was queried
        mock_conn.execute.assert_called_once_with("SELECT 1")

    @patch("src.health.DatabaseConnection")
    def test_database_check_failure(self, mock_db_class):
        """Test that database check returns error when database fails."""
        # Setup mock to raise exception
        mock_db_class.side_effect = Exception("Database connection failed")

        # Execute
        result = check_database()

        # Verify
        assert result["status"] == "error"
        assert "message" in result
        assert "error" in result["message"].lower()

    @patch("src.health.DatabaseConnection")
    def test_database_check_unexpected_result(self, mock_db_class):
        """Test that database check handles unexpected query results."""
        # Setup mock with unexpected result
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor

        mock_db = MagicMock()
        mock_db.connection = mock_conn
        mock_db_class.return_value = mock_db

        # Execute
        result = check_database()

        # Verify
        assert result["status"] == "error"
        assert "unexpected" in result["message"].lower()


class TestEventBusCheck:
    """Test suite for EventBus health check."""

    @patch("src.health.EventBus")
    def test_event_bus_check_success(self, mock_event_bus_class):
        """Test that event bus check returns ok when properly initialized."""
        # Setup mock
        mock_event_bus = MagicMock()
        mock_event_bus._subscribers = {
            "event1": [lambda x: x],
            "event2": [lambda x: x, lambda x: x],
        }
        mock_event_bus.publish = MagicMock()
        mock_event_bus_class.return_value = mock_event_bus

        # Execute
        result = check_event_bus()

        # Verify
        assert result["status"] == "ok"
        assert "message" in result
        assert result["subscribers"] == 3  # 1 + 2 subscribers

    @patch("src.health.EventBus")
    def test_event_bus_check_no_subscribers(self, mock_event_bus_class):
        """Test that event bus check works with no subscribers."""
        # Setup mock with no subscribers
        mock_event_bus = MagicMock()
        mock_event_bus._subscribers = {}
        mock_event_bus.publish = MagicMock()
        mock_event_bus_class.return_value = mock_event_bus

        # Execute
        result = check_event_bus()

        # Verify
        assert result["status"] == "ok"
        assert result["subscribers"] == 0

    @patch("src.health.EventBus")
    def test_event_bus_check_failure(self, mock_event_bus_class):
        """Test that event bus check returns error on failure."""
        # Setup mock to raise exception
        mock_event_bus_class.side_effect = Exception("EventBus initialization failed")

        # Execute
        result = check_event_bus()

        # Verify
        assert result["status"] == "error"
        assert "message" in result
        assert "error" in result["message"].lower()

    @patch("src.health.EventBus")
    def test_event_bus_check_missing_attributes(self, mock_event_bus_class):
        """Test that event bus check handles missing attributes."""
        # Setup mock without required attributes
        mock_event_bus = MagicMock()
        del mock_event_bus._subscribers
        mock_event_bus_class.return_value = mock_event_bus

        # Execute
        result = check_event_bus()

        # Verify
        assert result["status"] == "error"
        assert "not properly initialized" in result["message"].lower()


class TestUptimeCheck:
    """Test suite for uptime tracking."""

    def test_get_uptime_seconds_returns_positive(self):
        """Test that uptime is a positive number."""
        uptime = get_uptime_seconds()

        assert isinstance(uptime, float)
        assert uptime >= 0

    def test_get_uptime_increases(self):
        """Test that uptime increases over time."""
        uptime1 = get_uptime_seconds()
        time.sleep(0.1)
        uptime2 = get_uptime_seconds()

        assert uptime2 > uptime1


class TestOverallHealthCheck:
    """Test suite for overall health check."""

    @patch("src.health.check_database")
    @patch("src.health.check_event_bus")
    def test_health_check_all_ok(self, mock_event_bus_check, mock_db_check):
        """Test that health check returns healthy when all components are ok."""
        # Setup mocks
        mock_db_check.return_value = {"status": "ok", "message": "DB ok"}
        mock_event_bus_check.return_value = {"status": "ok", "message": "EventBus ok"}

        # Execute
        result = check_health()

        # Verify
        assert result["status"] == "healthy"
        assert result["checks"]["database"] == "ok"
        assert result["checks"]["event_bus"] == "ok"
        assert "timestamp" in result
        assert "version" in result
        assert result["version"] == "1.0.0"
        assert "uptime_seconds" in result
        assert "environment" in result

        # Should not have detailed error info when healthy
        assert "details" not in result

    @patch("src.health.check_database")
    @patch("src.health.check_event_bus")
    def test_health_check_database_error(self, mock_event_bus_check, mock_db_check):
        """Test that health check returns unhealthy when database fails."""
        # Setup mocks
        mock_db_check.return_value = {"status": "error", "message": "DB failed"}
        mock_event_bus_check.return_value = {"status": "ok", "message": "EventBus ok"}

        # Execute
        result = check_health()

        # Verify
        assert result["status"] == "unhealthy"
        assert result["checks"]["database"] == "error"
        assert result["checks"]["event_bus"] == "ok"

        # Should have detailed error info when unhealthy
        assert "details" in result
        assert "database" in result["details"]
        assert "event_bus" in result["details"]

    @patch("src.health.check_database")
    @patch("src.health.check_event_bus")
    def test_health_check_event_bus_error(self, mock_event_bus_check, mock_db_check):
        """Test that health check returns unhealthy when event bus fails."""
        # Setup mocks
        mock_db_check.return_value = {
            "status": "ok", "message": "DB ok",
        }
        mock_event_bus_check.return_value = {
            "status": "error",
            "message": "EventBus failed",
        }

        # Execute
        result = check_health()

        # Verify
        assert result["status"] == "unhealthy"
        assert result["checks"]["database"] == "ok"
        assert result["checks"]["event_bus"] == "error"

        # Should have detailed error info
        assert "details" in result

    @patch("src.health.check_database")
    @patch("src.health.check_event_bus")
    def test_health_check_all_error(self, mock_event_bus_check, mock_db_check):
        """Test that health check returns unhealthy when all components fail."""
        # Setup mocks
        mock_db_check.return_value = {
            "status": "error", "message": "DB failed",
        }
        mock_event_bus_check.return_value = {
            "status": "error",
            "message": "EventBus failed",
        }

        # Execute
        result = check_health()

        # Verify
        assert result["status"] == "unhealthy"
        assert result["checks"]["database"] == "error"
        assert result["checks"]["event_bus"] == "error"
        assert "details" in result

    @patch("src.health.check_database")
    @patch("src.health.check_event_bus")
    def test_health_check_includes_timestamp(self, mock_event_bus_check, mock_db_check):
        """Test that health check includes ISO format timestamp."""
        # Setup mocks
        mock_db_check.return_value = {"status": "ok", "message": "DB ok"}
        mock_event_bus_check.return_value = {"status": "ok", "message": "EventBus ok"}

        # Execute
        result = check_health()

        # Verify timestamp format (ISO 8601)
        assert "timestamp" in result
        assert "T" in result["timestamp"]
        assert "Z" in result["timestamp"] or "+" in result["timestamp"]

    @patch("src.health.check_database")
    @patch("src.health.check_event_bus")
    def test_health_check_includes_uptime(self, mock_event_bus_check, mock_db_check):
        """Test that health check includes uptime in seconds."""
        # Setup mocks
        mock_db_check.return_value = {"status": "ok", "message": "DB ok"}
        mock_event_bus_check.return_value = {"status": "ok", "message": "EventBus ok"}

        # Execute
        result = check_health()

        # Verify
        assert "uptime_seconds" in result
        assert isinstance(result["uptime_seconds"], (int, float))
        assert result["uptime_seconds"] >= 0

    @patch("src.health.check_database")
    @patch("src.health.check_event_bus")
    @patch("src.health.settings")
    def test_health_check_includes_environment(
        self, mock_settings, mock_event_bus_check,
        mock_db_check,
    ):
        """Test that health check includes environment information."""
        # Setup mocks
        mock_settings.app_env = "test"
        mock_db_check.return_value = {"status": "ok", "message": "DB ok"}
        mock_event_bus_check.return_value = {"status": "ok", "message": "EventBus ok"}

        # Execute
        result = check_health()

        # Verify
        assert "environment" in result
        assert result["environment"] == "test"
