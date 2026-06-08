"""Bounded retry with exponential backoff (SRS NFR-02 task reliability).

A tiny, dependency-free helper so transient failures (model API timeouts,
network blips) are retried automatically before a task is marked failed. The
``sleep`` callable is injectable so unit tests run without real delays.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Callable, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_DEFAULT_ATTEMPTS = 3
_DEFAULT_BASE_DELAY = 0.5
_DEFAULT_BACKOFF = 2.0


def default_attempts() -> int:
    raw = os.getenv("DVR_SEMANTIC_RETRY_ATTEMPTS", "").strip()
    if raw:
        try:
            value = int(raw)
            if value >= 1:
                return value
        except ValueError:
            pass
    return _DEFAULT_ATTEMPTS


def default_base_delay() -> float:
    raw = os.getenv("DVR_SEMANTIC_RETRY_BASE_DELAY", "").strip()
    if raw:
        try:
            value = float(raw)
            if value >= 0:
                return value
        except ValueError:
            pass
    return _DEFAULT_BASE_DELAY


def call_with_retry(
    func: Callable[[], T],
    *,
    attempts: int = _DEFAULT_ATTEMPTS,
    base_delay: float = 0.0,
    backoff: float = _DEFAULT_BACKOFF,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    on_retry: Callable[[int, BaseException], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``func`` up to ``attempts`` times, retrying on ``exceptions``.

    Raises the last exception if every attempt fails. ``base_delay`` of 0 means
    no sleeping between attempts (the default, so latency-sensitive callers opt
    in explicitly).
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except exceptions as exc:  # noqa: PERF203 - retry loop is the point
            last_exc = exc
            if attempt >= attempts:
                break
            if on_retry is not None:
                on_retry(attempt, exc)
            delay = base_delay * (backoff ** (attempt - 1)) if base_delay > 0 else 0.0
            logger.warning(
                "retry %d/%d after %s: %s (next delay %.2fs)",
                attempt,
                attempts,
                type(exc).__name__,
                exc,
                delay,
            )
            if delay > 0:
                sleep(delay)
    assert last_exc is not None  # loop body guarantees this on failure
    raise last_exc


__all__ = ["call_with_retry", "default_attempts", "default_base_delay"]
