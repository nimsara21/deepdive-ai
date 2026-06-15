import time
import random
from typing import Callable, TypeVar, Any
from functools import wraps

from .logging_config import logger

T = TypeVar("T")


class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff (delay *= base each retry)
            jitter: Add random jitter to avoid thundering herd
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number (0-indexed)."""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            jitter_amount = delay * 0.1  # ±10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0.1, delay)  # Ensure minimum 100ms


_DEFAULT_CONFIG = RetryConfig()


def _is_transient_error(exc: Exception) -> bool:
    """Check if an error is transient (worth retrying)."""
    exc_str = str(exc).lower()

    # Timeout errors
    if "timeout" in exc_str or "timed out" in exc_str:
        return True

    # Rate limiting
    if "rate limit" in exc_str or "429" in exc_str:
        return True

    # Temporary service unavailability
    if "503" in exc_str or "service unavailable" in exc_str:
        return True
    if "502" in exc_str or "bad gateway" in exc_str:
        return True

    # Connection errors
    if "connection" in exc_str or "network" in exc_str:
        return True

    return False


def with_retry(config: RetryConfig = _DEFAULT_CONFIG):
    """
    Decorator to add exponential backoff retry logic to a function.

    Args:
        config: RetryConfig instance with retry parameters
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exc = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc

                    # Don't retry non-transient errors
                    if not _is_transient_error(exc):
                        logger.error(f"{func.__name__} failed with non-transient error: {exc}")
                        raise

                    # On the last attempt, don't wait
                    if attempt >= config.max_retries:
                        logger.error(
                            f"{func.__name__} failed after {config.max_retries + 1} attempts"
                        )
                        raise

                    # Calculate delay and wait
                    delay = config.get_delay(attempt)
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{config.max_retries + 1} failed: {exc}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)

            # This should not be reached, but just in case
            raise last_exc

        return wrapper

    return decorator
