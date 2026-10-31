"""A thread-safe in-process token bucket for requests per minute (BR3.2, FR14.4)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class TokenBucket:
    """Allows ``rate_per_minute`` requests per minute, with bursts up to ``capacity``.

    ``take`` blocks until a token is free. A lock guards the token count, so concurrent
    callers never overdraw the bucket; the wait itself happens outside the lock.
    """

    def __init__(
        self,
        rate_per_minute: int,
        capacity: int | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if rate_per_minute < 1:
            raise ValueError("rate_per_minute must be at least 1")
        self._rate_per_s = rate_per_minute / 60.0
        self._capacity = float(capacity if capacity is not None else rate_per_minute)
        self._tokens = self._capacity
        self._clock = clock
        self._sleep = sleep
        self._updated = clock()
        self._lock = threading.Lock()

    def _try_take(self) -> float:
        """Take a token and return 0, or return how long to wait for the next one."""
        with self._lock:
            now = self._clock()
            elapsed = max(0.0, now - self._updated)
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate_per_s)
            self._updated = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return 0.0
            return (1.0 - self._tokens) / self._rate_per_s

    def take(self) -> float:
        """Block until a token is taken; return the seconds spent waiting."""
        waited = 0.0
        while (wait := self._try_take()) > 0:
            self._sleep(wait)
            waited += wait
        return waited
