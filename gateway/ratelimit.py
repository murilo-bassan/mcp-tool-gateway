"""Sliding-window rate limit per principal, in memory.

Good enough for one gateway process. Several replicas would move the
window to the database or Redis; the interface (`check`) stays the same.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from gateway.errors import RateLimited


class SlidingWindow:
    def __init__(self, limit: int, window_s: float = 60.0, clock=time.monotonic) -> None:
        self.limit = limit
        self.window_s = window_s
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> int:
        """Counts one hit for `key`; raises `RateLimited` past the limit. Returns hits left."""
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window_s:
                hits.popleft()
            if len(hits) >= self.limit:
                retry = round(hits[0] + self.window_s - now, 2)
                raise RateLimited(f"limit of {self.limit}/min reached", detail={"retry_after_s": retry})
            hits.append(now)
            return self.limit - len(hits)
