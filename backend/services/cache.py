"""
Tiny in-process TTL cache (per-worker).

Used to memoize deterministic, CPU-bound computations like panchang and
muhurat results. Per implementation.md §7 layer 2: ~4096 entries × ~2 KB
upper bound is cheap and keeps p95 latency low without Redis.

No external dependencies (avoids pulling cachetools just for this).
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable


class TTLCache:
    def __init__(self, maxsize: int = 4096, ttl_seconds: float = 3600.0) -> None:
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._data: "OrderedDict[Any, tuple[float, Any]]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any | None:
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at < now:
                self._data.pop(key, None)
                return None
            # LRU bump
            self._data.move_to_end(key)
            return value

    def set(self, key: Any, value: Any) -> None:
        expires_at = time.monotonic() + self._ttl
        with self._lock:
            self._data[key] = (expires_at, value)
            self._data.move_to_end(key)
            while len(self._data) > self._maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def ttl_cache(
    maxsize: int = 4096, ttl_seconds: float = 3600.0
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: memoize a pure function for ttl_seconds, LRU-evicted at maxsize."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        store = TTLCache(maxsize=maxsize, ttl_seconds=ttl_seconds)

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items()))) if kwargs else args
            hit = store.get(key)
            if hit is not None:
                return hit
            result = fn(*args, **kwargs)
            store.set(key, result)
            return result

        wrapper.cache_clear = store.clear  # type: ignore[attr-defined]
        return wrapper

    return decorator


# Shared header per implementation.md §7 layer 1 (CDN-friendly).
DEFAULT_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=86400"
