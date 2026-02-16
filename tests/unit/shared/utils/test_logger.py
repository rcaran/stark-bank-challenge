import json
import logging
from io import StringIO

from src.shared.utils.logger import StructuredLogger, get_logger


def test_structured_logger_format():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger = StructuredLogger("test_logger")
    # clear existing handlers to capture output in our stream
    logger.logger.handlers = []

    # recreate formatter setup from class
    formatter = logger.JsonFormatter()
    handler.setFormatter(formatter)
    logger.logger.addHandler(handler)
    logger.logger.setLevel(logging.INFO)

    logger.info("test message", key="value")

    log_output = stream.getvalue().strip()
    log_data = json.loads(log_output)

    assert log_data["level"] == "INFO"
    assert log_data["message"] == "test message"
    assert log_data["key"] == "value"
    assert "timestamp" in log_data
    assert log_data["logger"] == "test_logger"

def test_context_binding():
    # This implementation of bind just returns a new logger, simplistic.
    # But let's verify context passing in log calls.
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger = StructuredLogger("test_context", correlation_id="123")
    logger.logger.handlers = []
    handler.setFormatter(logger.JsonFormatter())
    logger.logger.addHandler(handler)
    logger.logger.setLevel(logging.INFO)

    logger.info("test context")

    log_output = stream.getvalue().strip()
    log_data = json.loads(log_output)

    assert log_data["correlation_id"] == "123"

def test_get_logger():
    logger = get_logger("my_module")
    assert isinstance(logger, StructuredLogger)
    assert logger.logger.name == "my_module"
