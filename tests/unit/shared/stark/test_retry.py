import pytest
import logging
from unittest.mock import MagicMock, patch
from src.shared.stark.retry import retry_with_backoff

# Mock logger
@pytest.fixture
def mock_logger(mocker):
    return mocker.patch("src.shared.stark.retry.logger")

def test_retry_success(mock_logger):
    mock_func = MagicMock(return_value="success")

    @retry_with_backoff(max_attempts=3, delays=[0, 0, 0])
    def decorated_func():
        return mock_func()

    result = decorated_func()
    assert result == "success"
    assert mock_func.call_count == 1
    mock_logger.warning.assert_not_called()

def test_retry_failure_then_success(mock_logger):
    # Fails first 2 times, succeeds on 3rd
    mock_func = MagicMock(side_effect=[ValueError("fail 1"), ValueError("fail 2"), "success"])

    @retry_with_backoff(max_attempts=3, delays=[0, 0, 0], retriable_exceptions=(ValueError,))
    def decorated_func():
        return mock_func()

    result = decorated_func()
    assert result == "success"
    assert mock_func.call_count == 3
    # Check if logger.warning was called for retries
    assert mock_logger.warning.call_count == 2 

def test_max_attempts_reached(mock_logger):
    mock_func = MagicMock(side_effect=ValueError("persistent failure"))

    @retry_with_backoff(max_attempts=3, delays=[0, 0, 0], retriable_exceptions=(ValueError,))
    def decorated_func():
        mock_func()

    with pytest.raises(ValueError, match="persistent failure"):
        decorated_func()
    
    assert mock_func.call_count == 3
    assert mock_logger.error.call_count >= 1 # Log max attempts reached

def test_non_retriable_exception(mock_logger):
    mock_func = MagicMock(side_effect=TypeError("fatal error"))

    @retry_with_backoff(
        max_attempts=3, 
        delays=[0, 0, 0], 
        retriable_exceptions=(ValueError,),
        non_retriable_exceptions=(TypeError,)
    )
    def decorated_func():
        mock_func()

    with pytest.raises(TypeError, match="fatal error"):
        decorated_func()

    assert mock_func.call_count == 1 # Should fail immediately
    mock_logger.error.assert_called() # Log non-retriable

def test_delays(mocker):
    mock_sleep = mocker.patch("time.sleep")
    mock_func = MagicMock(side_effect=[ValueError("fail 1"), ValueError("fail 2"), "success"])

    @retry_with_backoff(max_attempts=3, delays=[10, 20])
    def decorated_func():
        return mock_func()

    decorated_func()
    
    assert mock_sleep.call_count == 2
    mock_sleep.assert_has_calls([mocker.call(10), mocker.call(20)])
