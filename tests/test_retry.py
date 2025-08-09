import time
import logging

import pytest

from trading_bot.notify import configure
from trading_bot.utils.retry import RetryPolicy


def test_retry_succeeds_after_transient_failure(caplog):
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("boom")
        return "ok"

    policy = RetryPolicy(retries=5, backoff=0.01, jitter=0.0)
    with caplog.at_level(logging.WARNING):
        result = policy.call(flaky)
    assert result == "ok"
    assert calls["n"] == 3
    assert any("flaky failed" in r.message for r in caplog.records)


def test_circuit_breaker_opens_and_recovers(caplog, capfd):
    def always_fail():
        raise ValueError("nope")

    configure({"alerts": {"enabled": True}})
    policy = RetryPolicy(
        retries=0,
        backoff=0.01,
        jitter=0.0,
        failure_threshold=2,
        recovery_time=0.1,
    )
    with caplog.at_level(logging.WARNING):
        for _ in range(2):
            with pytest.raises(ValueError):
                policy.call(always_fail)
    with pytest.raises(RuntimeError):
        policy.call(always_fail)
    captured = capfd.readouterr()
    assert "Circuit breaker open" in captured.out
    assert any("Circuit breaker open" in r.message for r in caplog.records)
    time.sleep(0.2)

    def succeed():
        return 42

    assert policy.call(succeed) == 42
