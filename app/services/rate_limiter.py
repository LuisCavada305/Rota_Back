"""Rate limiter utilities resilient to multi-instance deployments."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, DefaultDict, Tuple
from urllib.parse import urlsplit

try:  # pragma: no cover - handled by runtime detection
    from redis import Redis, from_url
    from redis.exceptions import RedisError
except ModuleNotFoundError:  # pragma: no cover - redis is opcional
    Redis = None  # type: ignore
    from_url = None  # type: ignore

    class RedisError(Exception):
        """Fallback exception when redis is unavailable."""

        pass

from app.core.settings import settings

LOGGER = logging.getLogger(__name__)


def _mask_redis_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return "redis://<invalid>"

    host = parsed.hostname or "localhost"
    port = f":{parsed.port}" if parsed.port else ""
    db = parsed.path or ""
    return f"{parsed.scheme}://{host}{port}{db}" if parsed.scheme else f"redis://{host}{port}{db}"


class FixedWindowRateLimiter:
    """Track attempts per key within a rolling time window (in-memory)."""

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


_RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local retry_after = 0
  if oldest[2] then
    retry_after = oldest[2] + window - now
  else
    retry_after = window
  end
  return {0, retry_after}
end

redis.call('ZADD', key, now, now)
redis.call('EXPIRE', key, window)
return {1, 0}
"""


class RedisFixedWindowRateLimiter:
    """Fixed window limiter backed by Redis sorted sets."""

    def __init__(
        self,
        client: "Redis",
        max_attempts: int,
        window_seconds: int,
        *,
        namespace: str = "auth",
    ) -> None:
        self._client = client
        self._max_attempts = int(max_attempts)
        self._window = float(window_seconds)
        self._namespace = namespace
        self._script = client.register_script(_RATE_LIMIT_LUA)

    def _key(self, key: str) -> str:
        return f"rate:{self._namespace}:{key}"

    def register_attempt(self, key: str) -> Tuple[bool, float | None]:
        now = time.time()
        allowed, retry_after = self._script(
            keys=[self._key(key)],
            args=[now, self._window, self._max_attempts],
        )
        if int(allowed):
            return True, None
        retry_after = float(retry_after)
        return False, max(retry_after, 0.0)


def _build_auth_limiter():
    if settings.redis_url and from_url and Redis is not None:
        try:
            client = from_url(settings.redis_url, decode_responses=False)
            LOGGER.info(
                "Usando Redis para rate limiting",
                extra={"redis": _mask_redis_url(settings.redis_url)},
            )
            return RedisFixedWindowRateLimiter(
                client,
                max_attempts=settings.auth_rate_limit_max_attempts,
                window_seconds=settings.auth_rate_limit_window_seconds,
            )
        except RedisError as exc:
            LOGGER.warning(
                "Falha ao inicializar Redis para rate limiting; usando memória local",
                exc_info=exc,
            )
    elif settings.redis_url:
        LOGGER.warning(
            "Redis não está disponível no ambiente atual; usando rate limiting em memória"
        )
    return FixedWindowRateLimiter(
        max_attempts=settings.auth_rate_limit_max_attempts,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )


_auth_limiter = _build_auth_limiter()


def check_auth_rate_limit(identifier: str) -> float | None:
    """Check whether the identifier can perform another auth attempt."""

    allowed, retry_after = _auth_limiter.register_attempt(identifier)
    if allowed:
        return None
    return retry_after or 0.0
