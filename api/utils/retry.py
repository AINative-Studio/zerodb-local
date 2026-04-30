"""
Retry Utility with Exponential Backoff
Provides decorator for retrying failed operations with configurable backoff
"""
import asyncio
import logging
from functools import wraps
from typing import Callable, Optional, Tuple, Type
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 1.0)
        max_delay: Maximum delay in seconds between retries (default: 30.0)
        exponential_base: Base for exponential backoff calculation (default: 2.0)
        timeout: Maximum total time for all retries in seconds (default: 300.0)
        retryable_status_codes: HTTP status codes that should trigger retry
    """
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    timeout: float = 300.0
    retryable_status_codes: Tuple[int, ...] = (500, 502, 503, 504, 408)


def with_retry(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying async functions with exponential backoff

    Args:
        config: RetryConfig instance (uses defaults if None)
        retryable_exceptions: Tuple of exception types that should trigger retry

    Example:
        @with_retry(config=RetryConfig(max_retries=5))
        async def fetch_data():
            # Function that may fail transiently
            return await api_call()
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            start_time = asyncio.get_event_loop().time()

            for attempt in range(config.max_retries + 1):
                try:
                    # Check timeout
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > config.timeout:
                        logger.error(
                            f"{func.__name__}: Total timeout exceeded "
                            f"({elapsed:.2f}s > {config.timeout}s)"
                        )
                        raise TimeoutError(
                            f"Total retry timeout exceeded: {elapsed:.2f}s"
                        )

                    # Attempt function call
                    logger.debug(
                        f"{func.__name__}: Attempt {attempt + 1}/{config.max_retries + 1}"
                    )
                    result = await func(*args, **kwargs)

                    # Success
                    if attempt > 0:
                        logger.info(
                            f"{func.__name__}: Succeeded on attempt {attempt + 1}"
                        )
                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    # Check if this is an HTTP error with retryable status code
                    if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                        status_code = e.response.status_code
                        if status_code not in config.retryable_status_codes:
                            logger.warning(
                                f"{func.__name__}: Non-retryable status code {status_code}"
                            )
                            raise

                    # Don't retry on last attempt
                    if attempt == config.max_retries:
                        logger.error(
                            f"{func.__name__}: All {config.max_retries + 1} attempts failed"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        config.initial_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )

                    logger.warning(
                        f"{func.__name__}: Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    await asyncio.sleep(delay)

            # Should never reach here, but just in case
            raise last_exception if last_exception else Exception("Retry failed")

        return wrapper
    return decorator


class RetryableHTTPError(Exception):
    """
    Exception for HTTP errors that should be retried
    Includes response object for status code checking
    """
    def __init__(self, message: str, response=None):
        super().__init__(message)
        self.response = response
