from src.shared.utils.errors import (
    StarkBankError, RetriableError, NonRetriableError,
    ValidationError, AuthenticationError, NotFoundError,
    TimeoutError, RateLimitError
)

def test_exception_hierarchy():
    assert issubclass(RetriableError, StarkBankError)
    assert issubclass(NonRetriableError, StarkBankError)
    assert issubclass(ValidationError, NonRetriableError)
    assert issubclass(AuthenticationError, NonRetriableError)
    assert issubclass(NotFoundError, NonRetriableError)
    assert issubclass(TimeoutError, RetriableError)
    assert issubclass(RateLimitError, RetriableError)

def test_exception_messages():
    error = StarkBankError("test message", {"key": "value"})
    assert str(error) == "test message"
    assert error.details == {"key": "value"}
