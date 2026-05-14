"""Tiny in-memory TTL cache. Thread-safe enough for Streamlit's single process."""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int = 900):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            ts, value = item
            if time.time() - ts > self.ttl:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.time(), value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def memoize(self, key: str, producer: Callable[[], Any]) -> Any:
        existing = self.get(key)
        if existing is not None:
            return existing
        value = producer()
        self.set(key, value)
        return value
