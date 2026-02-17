"""Retry decorator for handling transient failures."""

import functools
import logging
import time

from src.config.constants import RETRY_DELAYS, RETRY_MAX_ATTEMPTS

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int | None = None,
    delays: list[int] | None = None,
    retriable_exceptions: type[Exception] | tuple = (Exception,),
    non_retriable_exceptions: type[Exception] | tuple = (),
):
    """
    Decorator for retrying a function with custom backoff delays.

    :param max_attempts: Maximum number of attempts (including the first one).
                        If not provided, defaults to RETRY_MAX_ATTEMPTS from constants.
    :param delays: List of delays in seconds for each retry. If not provided,
                   defaults to RETRY_DELAYS from constants.
                   Length should be at least max_attempts - 1.
    :param retriable_exceptions: Exceptions that trigger a retry. Default: Exception.
    :param non_retriable_exceptions: Exceptions that stop retries immediately.
                                     Default: ().
    """
    if delays is None:
        delays = RETRY_DELAYS  # Use constant from config
    if max_attempts is None:
        max_attempts = RETRY_MAX_ATTEMPTS  # Use constant from config

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except non_retriable_exceptions as e:
                    logger.error(f"Non-retriable exception in {func.__name__}: {e}")
                    raise e
                except retriable_exceptions as e:
                    attempt += 1
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed in "
                        f"{func.__name__}: {e}"
                    )

                    if attempt >= max_attempts:
                        logger.error(f"Max attempts reached for {func.__name__}.")
                        raise e

                    if (attempt - 1) < len(delays):
                        delay = delays[attempt - 1]
                    else:
                        delay = delays[-1]
                    if delay > 0:
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                except Exception as e:
                    # Non-retriable exception, re-raise immediately
                    raise e
            return None  # Should not be reached

        return wrapper

    return decorator
