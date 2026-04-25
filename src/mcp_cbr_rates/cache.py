"""Tiny asyncio-friendly TTL (Time-To-Live) cache.

Used to throttle CBR HTTP calls. Daily lookups expire after one hour, historical
series after a day. Eviction is lazy (on get) and on explicit ``prune``.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float


class TTLCache:
    """Simple in-process cache with per-key TTL.

    Concurrency-safe under cooperative async usage: an internal asyncio lock
    guards mutation. Reads are still O(1).
    """

    def __init__(self, default_ttl: float = 3600.0) -> None:
        self._default_ttl = float(default_ttl)
        self._store: dict[str, _Entry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            async with self._lock:
                self._store.pop(key, None)
            return None
        return entry.value

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        ttl_seconds = self._default_ttl if ttl is None else float(ttl)
        async with self._lock:
            self._store[key] = _Entry(value=value, expires_at=time.monotonic() + ttl_seconds)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def prune(self) -> int:
        """Remove all expired entries. Returns the number of removed keys."""
        now = time.monotonic()
        async with self._lock:
            stale = [k for k, e in self._store.items() if e.expires_at <= now]
            for key in stale:
                self._store.pop(key, None)
            return len(stale)

    def __len__(self) -> int:  # pragma: no cover - debugging aid
        return len(self._store)
