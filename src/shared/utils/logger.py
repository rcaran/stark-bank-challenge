import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional

from src.config.settings import settings


class StructuredLogger:
    def __init__(self, name: str, correlation_id: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, settings.log_level.upper()))
        self.correlation_id = correlation_id

        # Prevent adding multiple handlers if logger already exists
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = self.JsonFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log_record = {
                "timestamp": datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).isoformat(),
                "level": record.levelname,

                "logger": record.name,
                "message": record.getMessage(),
                "correlation_id": getattr(record, "correlation_id", None),
            }

            if hasattr(record, "props"):
                log_record.update(record.props)

            if record.exc_info:
                log_record["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_record)

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

    def bind(self, **kwargs: Any) -> "StructuredLogger":
        """Returns a new logger instance with bound context"""
        new_logger = StructuredLogger(self.logger.name, self.correlation_id)
        # In a real implementation we might want to attach context permanently
        # For simplicity, we return a new logger here, context is per-log call
        # or we could implement a ContextVar based context.
        return new_logger

def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
