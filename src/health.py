"""
Health Check Module.

This module provides health check functionality to verify that
all system components are working correctly.
"""

import time
from datetime import UTC, datetime

from src.config.settings import settings
from src.shared.database.connection import DatabaseConnection
from src.shared.events.bus import EventBus
from src.shared.utils.logger import get_logger

logger = get_logger("health")

# Track application start time
_start_time = time.time()


def check_database() -> dict[str, any]:
    """
    Check if database is accessible and working.

    Returns:
        Dict with status and details
    """
    try:
        db = DatabaseConnection()
        conn = db.connection

        # Execute simple query to verify connectivity
        cursor = conn.execute("SELECT 1")
        result = cursor.fetchone()

        if result and result[0] == 1:
            return {
                "status": "ok",
                "message": "Database connection successful"
            }
        return {
            "status": "error",
            "message": "Database query returned unexpected result"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e!s}")
        return {
            "status": "error",
            "message": f"Database error: {e!s}"
        }


def check_event_bus() -> dict[str, any]:
    """
    Check if EventBus is initialized and working.

    Returns:
        Dict with status and details
    """
    try:
        event_bus = EventBus()

        # Check if event bus has the expected structure
        if hasattr(event_bus, "_subscribers") and hasattr(
            event_bus, "publish"
        ):
            subscriber_count = sum(
                len(handlers) for handlers in event_bus._subscribers.values()
            )
            return {
                "status": "ok",
                "message": "EventBus operational",
                "subscribers": subscriber_count
            }
        return {
            "status": "error",
            "message": "EventBus not properly initialized"
        }
    except Exception as e:
        logger.error(f"EventBus health check failed: {e!s}")
        return {
            "status": "error",
            "message": f"EventBus error: {e!s}"
        }


def get_uptime_seconds() -> float:
    """
    Get application uptime in seconds.

    Returns:
        Uptime in seconds
    """
    return time.time() - _start_time


def check_health(include_stark: bool = False) -> dict[str, any]:
    """
    Perform comprehensive health check of all system components.

    Args:
        include_stark: Whether to include Stark Bank API check (slower)

    Returns:
        Dict with overall status and individual component checks
    """
    logger.debug("Running health check")

    # Check individual components
    db_check = check_database()
    event_bus_check = check_event_bus()

    # Determine overall status
    checks = {
        "database": db_check["status"],
        "event_bus": event_bus_check["status"]
    }

    # If any check failed, overall status is unhealthy
    overall_status = "healthy" if all(
        status == "ok" for status in checks.values()
    ) else "unhealthy"

    # Build response
    response = {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
        "version": "1.0.0",
        "uptime_seconds": round(get_uptime_seconds(), 2),
        "environment": settings.app_env
    }

    # Add detailed check info if unhealthy
    if overall_status == "unhealthy":
        response["details"] = {
            "database": db_check,
            "event_bus": event_bus_check
        }

    logger.debug(f"Health check completed: {overall_status}")

    return response
