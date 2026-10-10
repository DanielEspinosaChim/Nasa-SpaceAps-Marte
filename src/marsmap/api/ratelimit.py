"""Límite de peticiones por IP en ventana deslizante de 60 s (en memoria, por proceso)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

MAX_TRACKED_IPS = 10_000


class RateLimiter:
    def __init__(self, per_minute: int, window_s: float = 60.0, clock=time.monotonic):
        self.per_minute, self.window_s, self.clock = per_minute, window_s, clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self._lock:
            if len(self._hits) > MAX_TRACKED_IPS:  # evita crecer sin límite ante IPs falsas
                self._hits = defaultdict(
                    deque,
                    {k: v for k, v in self._hits.items() if v and now - v[-1] < self.window_s},
                )
            q = self._hits[key]
            while q and now - q[0] >= self.window_s:
                q.popleft()
            if len(q) >= self.per_minute:
                return False
            q.append(now)
            return True
