"""Retry configuration for external API calls."""

import logging
from collections.abc import Callable
from typing import Any

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("app.retry")


def log_retry(retry_state: RetryCallState) -> None:
    """Log retry attempts."""
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "Retrying %s (attempt %d/%d) after error: %s",
        retry_state.fn.__name__ if retry_state.fn else "unknown",
        retry_state.attempt_number,
        retry_state.retry_object.stop.max_attempt_number,  # type: ignore
        str(exception),
    )


# Exceptions that indicate transient failures worth retrying
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
)


def with_retry(
    max_attempts: int = 3,
    max_wait: int = 10,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for retrying functions on transient failures.

    Args:
        max_attempts: Maximum number of retry attempts
        max_wait: Maximum wait time between retries in seconds

    Usage:
        @with_retry(max_attempts=3)
        async def call_external_api():
            ...
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=max_wait),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=log_retry,
        reraise=True,
    )


# Pre-configured retry decorators for common use cases
retry_llm = with_retry(max_attempts=3, max_wait=10)
retry_vector_db = with_retry(max_attempts=2, max_wait=5)
retry_external_api = with_retry(max_attempts=3, max_wait=15)
