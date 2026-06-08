"""Unit tests for the bounded-retry helper (NFR-02 task reliability)."""
from __future__ import annotations

import importlib

import pytest

retry = importlib.import_module("dvr_semantic_backend.services.retry")


def test_succeeds_after_transient_failures() -> None:
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    result = retry.call_with_retry(flaky, attempts=3, sleep=lambda _: None)
    assert result == "ok"
    assert calls["n"] == 3


def test_raises_after_exhausting_attempts() -> None:
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise ValueError("nope")

    with pytest.raises(ValueError):
        retry.call_with_retry(always_fails, attempts=3, sleep=lambda _: None)
    assert calls["n"] == 3


def test_no_retry_on_unlisted_exception() -> None:
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        raise KeyError("unexpected")

    with pytest.raises(KeyError):
        retry.call_with_retry(
            boom, attempts=3, exceptions=(ValueError,), sleep=lambda _: None
        )
    assert calls["n"] == 1  # not retried


def test_on_retry_callback_and_backoff_delays() -> None:
    delays: list[float] = []
    seen: list[int] = []

    def flaky():
        raise RuntimeError("x")

    with pytest.raises(RuntimeError):
        retry.call_with_retry(
            flaky,
            attempts=3,
            base_delay=0.5,
            backoff=2.0,
            on_retry=lambda attempt, exc: seen.append(attempt),
            sleep=delays.append,
        )
    # two sleeps between three attempts, exponential: 0.5, 1.0
    assert delays == [0.5, 1.0]
    assert seen == [1, 2]


def test_invalid_attempts_rejected() -> None:
    with pytest.raises(ValueError):
        retry.call_with_retry(lambda: None, attempts=0)
