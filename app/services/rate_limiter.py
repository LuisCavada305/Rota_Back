"""Simple in-memory rate limiter utilities for protecting sensitive endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict, Tuple
from threading import Lock


class FixedWindowRateLimiter:
    """Track attempts per key within a rolling time window."""

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._window = float(window_seconds)
        self._hits: DefaultDict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def register_attempt(self, key: str) -> Tuple[bool, float | None]:
        """Record a hit and return whether it's allowed and next allowed timestamp."""

        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._max_attempts:
                retry_after = bucket[0] + self._window - now
                return False, max(retry_after, 0.0)
            bucket.append(now)
            return True, None


_auth_limiter = FixedWindowRateLimiter(max_attempts=10, window_seconds=60)


def check_auth_rate_limit(identifier: str) -> float | None:
    """Check whether the identifier can perform another auth attempt."""

    allowed, retry_after = _auth_limiter.register_attempt(identifier)
    if allowed:
        return None
    return retry_after or 0.0
