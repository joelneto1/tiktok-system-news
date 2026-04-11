from collections.abc import Callable
from functools import wraps
from typing import Any

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.utils.logger import logger


def _log_before_retry(retry_state: RetryCallState) -> None:
    """Log each retry attempt via loguru."""
    attempt = retry_state.attempt_number
    fn_name = getattr(retry_state.fn, "__name__", str(retry_state.fn))
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "Retrying {fn} (attempt {attempt}) after error: {err}",
        fn=fn_name,
        attempt=attempt,
        err=exception,
    )


def retry_async(
    max_attempts: int = 3,
    backoff_start: float = 2.0,
    backoff_max: float = 30.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable:
    """Tenacity retry decorator for async functions.

    Args:
        max_attempts: Maximum number of attempts before giving up.
        backoff_start: Initial wait in seconds (doubles each retry).
        backoff_max: Cap on the exponential backoff wait.
        exceptions: Tuple of exception types that trigger a retry.

    Usage::

        @retry_async(max_attempts=5, exceptions=(httpx.HTTPError,))
        async def call_external_api():
            ...
    """

    def decorator(fn: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=backoff_start, max=backoff_max),
            retry=retry_if_exception_type(exceptions),
            before_sleep=_log_before_retry,
            reraise=True,
        )
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await fn(*args, **kwargs)

        return wrapper

    return decorator


__all__ = ["retry_async"]
