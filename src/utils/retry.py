import logging
import random
import time
from functools import wraps
from typing import Callable, \
    Tuple, \
    Type

from ..api.exceptions import KeapRateLimitError

logger = logging.getLogger(__name__)


def exponential_backoff(max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 60.0, exponential_base: float = 2.0, jitter: bool = True,
                        exceptions: Tuple[Type[Exception], ...] = (KeapRateLimitError,)) -> Callable:
    """
    Decorator that implements exponential backoff with jitter for retrying operations
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential calculation
        jitter: Whether to add random jitter to delay
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args,
                                **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded. "
                                     f"Last error: {str(e)}")
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt),
                                max_delay)

                    # Add jitter if enabled
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed. "
                                   f"Retrying in {delay:.2f} seconds. Error: {str(e)}")

                    time.sleep(delay)

            # This should never be reached due to the raise in the loop
            raise last_exception

        return wrapper

    return decorator
