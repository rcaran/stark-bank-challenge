"""Custom exception classes for the application."""

from typing import Any


class StarkBankError(Exception):
    """Base exception for all Stark Bank Challenge errors"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class RetriableError(StarkBankError):
    """Errors that can be retried"""


class NonRetriableError(StarkBankError):
    """Errors that should not be retried"""


class ValidationError(NonRetriableError):
    """Validation errors"""


class AuthenticationError(NonRetriableError):
    """Authentication errors"""


class NotFoundError(NonRetriableError):
    """Resource not found errors"""


class TimeoutError(RetriableError):
    """Timeout errors"""


class RateLimitError(RetriableError):
    """Rate limit exceeded errors"""
