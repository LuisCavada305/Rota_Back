import pytest

from app.services import rate_limiter as rate_limiter_module
from app.services.rate_limiter import FixedWindowRateLimiter


def test_fixed_window_rate_limiter_blocks_after_threshold(monkeypatch):
    current_time = {"value": 1000.0}

    def fake_time():
        return current_time["value"]

    monkeypatch.setattr(rate_limiter_module.time, "time", fake_time)
    monkeypatch.setattr(rate_limiter_module.time, "monotonic", fake_time)

    limiter = FixedWindowRateLimiter(max_attempts=2, window_seconds=60)
    assert limiter.register_attempt("user")[0] is True
    assert limiter.register_attempt("user")[0] is True

    allowed, retry_after = limiter.register_attempt("user")
    assert allowed is False
    assert retry_after is not None and retry_after > 0

    current_time["value"] += 61
    allowed, retry_after = limiter.register_attempt("user")
    assert allowed is True
    assert retry_after is None
