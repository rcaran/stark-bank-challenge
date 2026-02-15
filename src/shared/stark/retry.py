import functools
import logging
import time
from typing import List, Optional, Type, Union

logger = logging.getLogger(__name__)

def retry_with_backoff(
    max_attempts: int = 5,
    delays: Optional[List[int]] = None,
    retriable_exceptions: Union[Type[Exception], tuple] = (Exception,),
    non_retriable_exceptions: Union[Type[Exception], tuple] = (),
):
    """
    Decorator for retrying a function with custom backoff delays.

    :param max_attempts: Maximum number of attempts (including the first one).
    :param delays: List of delays in seconds for each retry. If not provided,
                   defaults to [0, 60, 120, 240, 480].
                   Length should be at least max_attempts - 1.
    :param retriable_exceptions: Exceptions that trigger a retry. Default: Exception.
    :param non_retriable_exceptions: Exceptions that stop retries immediately.
                                     Default: ().
    """
    if delays is None:
        delays = [0, 60, 120, 240, 480]  # Default delays

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
                    # Unexpected exception, not in retriable/non_retriable
                    # list (if retriable is specific)
                    # If retriable_exceptions is (Exception,), this block won't be
                    # reached for standard exceptions unless retriable was narrowed.
                    # Assuming default (Exception,), everything is caught above
                    # unless non_retriable matches.
                    # If retriable is specific, e.g. (ValueError,), and we get
                    # TypeError, we should raise.
                    raise e
            return None # Should not be reached
        return wrapper
    return decorator
