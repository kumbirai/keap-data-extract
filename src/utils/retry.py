import logging
import random
import time
from functools import wraps
from typing import Callable, Dict, Optional, Tuple, Type

# Remove the circular import - we'll handle exceptions by name instead
# from ..api.exceptions import KeapQuotaExhaustedError, KeapRateLimitError

logger = logging.getLogger(__name__)


def get_throttle_retry_delay(headers: Dict[str, str], throttle_available: int, tenant_available: int) -> Optional[float]:
    """
    Calculate the appropriate retry delay based on Keap's throttle headers
    
    Args:
        headers: Response headers containing throttle information
        throttle_available: Available product throttle requests
        tenant_available: Available tenant throttle requests
        
    Returns:
        Float delay in seconds, or None if no retry is needed
    """
    # If we have available requests in both categories, no need to retry
    if throttle_available > 0 and tenant_available > 0:
        return None

    # For throttle limits, wait for the next minute with some jitter
    # This prevents all clients from retrying at exactly the same time
    # Add extra jitter (0-10 seconds) to help prevent thundering herd
    return 60.0 + random.uniform(0, 10.0)  # 60-70 seconds


def safe_int_parse(value, default=0):
    """Safely parse integer from header value, handling empty strings"""
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def exponential_backoff(max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 60.0, exponential_base: float = 2.0, jitter: bool = True, exceptions: Tuple[
    Type[Exception], ...] = None) -> Callable:
    """
    Decorator that implements intelligent backoff for retrying operations, with special handling for Keap's throttle limits
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds (only used for non-rate-limit errors)
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential calculation (only used for non-rate-limit errors)
        jitter: Whether to add random jitter to delay (only used for non-rate-limit errors)
        exceptions: Tuple of exceptions to catch and retry on (KeapQuotaExhaustedError is never retried)
        
    Returns:
        Decorated function with retry logic
    """
    # Import here to avoid circular import and ensure availability in function scope
    from ..api.exceptions import KeapQuotaExhaustedError, KeapRateLimitError

    # Default exceptions if none provided
    if exceptions is None:
        exceptions = (KeapRateLimitError,)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            attempt = 0

            while attempt <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    # Never retry on quota exhaustion
                    if isinstance(e, KeapQuotaExhaustedError):
                        raise

                    last_exception = e
                    attempt += 1

                    if attempt > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded. Last error: {str(e)}")
                        raise

                    # Special handling for rate limit errors
                    if isinstance(e, KeapRateLimitError):
                        # Extract throttle information from the error message
                        # Format: "Rate limit exceeded (TYPE, limit: X). Will retry after throttle period."
                        try:
                            # Get headers from the last response if available
                            headers = getattr(e, 'response_headers', {}) or {}

                            # Get throttle values from headers with safe defaults
                            throttle_available = safe_int_parse(headers.get('x-keap-product-throttle-available'))
                            tenant_available = safe_int_parse(headers.get('x-keap-tenant-throttle-available'))

                            # Calculate delay based on throttle type
                            delay = get_throttle_retry_delay(headers, throttle_available, tenant_available)

                            if delay is None:
                                # If we have available requests, retry immediately
                                logger.info("Throttle headers indicate requests are available, retrying immediately")
                                continue

                            logger.warning(f"Throttle limit hit. Waiting {delay:.2f} seconds before retry. "
                                           f"Available: Throttle={throttle_available}, Tenant={tenant_available}")

                        except (ValueError, AttributeError) as parse_error:
                            # If we can't parse the error message or headers, fall back to exponential backoff
                            logger.warning(f"Could not parse throttle error: {parse_error}. Using exponential backoff.")
                            delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                            if jitter:
                                delay = delay * (0.5 + random.random())
                    else:
                        # For non-rate-limit errors, use standard exponential backoff
                        delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                        if jitter:
                            delay = delay * (0.5 + random.random())
                        logger.warning(f"Attempt {attempt}/{max_retries} failed. "
                                       f"Retrying in {delay:.2f} seconds. Error: {str(e)}")

                    time.sleep(delay)

            # This should never be reached due to the raise in the loop
            raise last_exception

        return wrapper

    return decorator
