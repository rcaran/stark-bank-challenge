from typing import Any, Dict, Optional


class StarkBankError(Exception):
    """Base exception for all Stark Bank Challenge errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class RetriableError(StarkBankError):
    """Errors that can be retried"""
    pass

class NonRetriableError(StarkBankError):
    """Errors that should not be retried"""
    pass

class ValidationError(NonRetriableError):
    """Validation errors"""
    pass

class AuthenticationError(NonRetriableError):
    """Authentication errors"""
    pass

class NotFoundError(NonRetriableError):
    """Resource not found errors"""
    pass

class TimeoutError(RetriableError):
    """Timeout errors"""
    pass

class RateLimitError(RetriableError):
    """Rate limit exceeded errors"""
    pass
