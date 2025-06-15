import logging
import random
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Callable, Dict, Optional, Tuple, Type

from ..api.exceptions import KeapRateLimitError, KeapQuotaExhaustedError

logger = logging.getLogger(__name__)


def get_retry_delay(headers: Dict[str, str], quota_available: int, throttle_available: int, tenant_available: int) -> Optional[float]:
    """
    Calculate the appropriate retry delay based on Keap's rate limit headers
    
    Args:
        headers: Response headers containing quota and throttle information
        quota_available: Available quota requests
        throttle_available: Available throttle requests
        tenant_available: Available tenant throttle requests
        
    Returns:
        Float delay in seconds, or None if no retry is needed
    """
    # If we have available requests in all categories, no need to retry
    if quota_available > 0 and throttle_available > 0 and tenant_available > 0:
        return None
        
    # Get the most restrictive limit
    if quota_available == 0:
        # For quota limits, we need to wait until the next quota period
        expiry_time = headers.get('x-keap-product-quota-expiry-time')
        if expiry_time:
            try:
                expiry = int(expiry_time)
                now = int(datetime.now(timezone.utc).timestamp())
                return max(1.0, expiry - now)  # Minimum 1 second delay
            except (ValueError, TypeError):
                pass
        # If we can't parse expiry time, use a conservative delay
        return 3600.0  # 1 hour default for quota limits
        
    elif throttle_available == 0 or tenant_available == 0:
        # For throttle limits, wait for the next minute
        # Add some jitter to prevent all clients from retrying at exactly the same time
        return 60.0 + random.uniform(0, 5.0)  # 60-65 seconds
        
    return None


def exponential_backoff(max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 3600.0, exponential_base: float = 2.0, jitter: bool = True,
                        exceptions: Tuple[Type[Exception], ...] = (KeapRateLimitError,)) -> Callable:
    """
    Decorator that implements intelligent backoff for retrying operations, with special handling for Keap's rate limits
    
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
                        # Extract rate limit information from the error message
                        # Format: "Rate limit exceeded. Available: Quota=X, Throttle=Y, Tenant=Z. Time unit: UNIT"
                        try:
                            parts = str(e).split('Available: ')[1].split('.')[0]
                            quota = int(parts.split('Quota=')[1].split(',')[0])
                            throttle = int(parts.split('Throttle=')[1].split(',')[0])
                            tenant = int(parts.split('Tenant=')[1].split('.')[0])
                            
                            # Get headers from the last response if available
                            headers = getattr(e, 'response_headers', {})
                            
                            # Calculate delay based on rate limit type
                            delay = get_retry_delay(headers, quota, throttle, tenant)
                            
                            if delay is None:
                                # If we have available requests, retry immediately
                                logger.info("Rate limit headers indicate requests are available, retrying immediately")
                                continue
                                
                            logger.warning(f"Rate limit hit. Waiting {delay:.2f} seconds before retry. "
                                         f"Available: Quota={quota}, Throttle={throttle}, Tenant={tenant}")
                            
                        except (IndexError, ValueError) as parse_error:
                            # If we can't parse the error message, fall back to exponential backoff
                            logger.warning(f"Could not parse rate limit error: {parse_error}. Using exponential backoff.")
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
