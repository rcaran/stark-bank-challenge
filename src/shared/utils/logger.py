"""Structured logging utilities for the application."""

import json
import logging
import logging.config
from datetime import UTC, datetime
from typing import Any

from src.config.settings import settings


class JsonFormatter(logging.Formatter):
    """JSON formatter compatible with Railway's log instrumentation.

    Outputs a single JSON object per line with the fields Railway expects:
    - ``timestamp``: ISO-8601 with timezone
    - ``level``: log level string (INFO, ERROR …)
    - ``logger``: logger name
    - ``message``: human-readable log message
    """

    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
        }

        if hasattr(record, "props"):
            log_record.update(record.props)

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, default=str)


def setup_logging() -> None:
    """Configure all loggers (including uvicorn) to emit JSON to stdout.

    Must be called once at application startup, before any logger is used,
    so that Railway's log drain can parse every line as structured JSON.
    """
    log_level = settings.log_level.upper()

    logging_config: dict[str, Any] = {
        "version": 1,
        # Keep existing loggers that may have been created by imported libs
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JsonFormatter,
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "json",
            }
        },
        "root": {
            "handlers": ["stdout"],
            "level": log_level,
        },
        "loggers": {
            # Uvicorn access log — one entry per HTTP request
            "uvicorn.access": {
                "handlers": ["stdout"],
                "level": "INFO",
                "propagate": False,
            },
            # Uvicorn error/lifecycle messages
            "uvicorn.error": {
                "handlers": ["stdout"],
                "level": log_level,
                "propagate": False,
            },
            # Uvicorn root
            "uvicorn": {
                "handlers": ["stdout"],
                "level": log_level,
                "propagate": False,
            },
            # SQLAlchemy — only warn by default to avoid query noise
            "sqlalchemy.engine": {
                "handlers": ["stdout"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)


class StructuredLogger:
    def __init__(self, name: str, correlation_id: str | None = None):
        self.logger = logging.getLogger(name)
        self.correlation_id = correlation_id

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        extra = {"props": kwargs}
        if self.correlation_id:
            extra["correlation_id"] = self.correlation_id

        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, message, **kwargs)

    def bind(self) -> StructuredLogger:
        """Returns a new logger instance with bound context"""
        return StructuredLogger(self.logger.name, self.correlation_id)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
