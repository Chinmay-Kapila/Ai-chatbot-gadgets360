"""
Simple in-memory TTL cache service.

Used to cache:
  - Parser JSON output (so identical queries don't re-hit Gemini).
  - Common, non-personalized API responses (e.g. price, product
    listings) to reduce upstream calls.

Personalized responses (tied to a specific session's conversation) are
NEVER cached. No external cache/database is used — this is a pure
in-process dictionary with TTL eviction and a max-size bound.
"""

import asyncio
import time
from typing import Any, Dict, Optional, Tuple

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TTLCache:
    """A minimal thread-safe-enough (asyncio-lock-guarded) in-memory TTL cache."""

    def __init__(self, max_entries: int = 1000):
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._max_entries = max_entries
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None

            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                return None

            return value

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        async with self._lock:
            if len(self._store) >= self._max_entries:
                self._evict_oldest()

            expires_at = time.time() + ttl_seconds
            self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    def _evict_oldest(self) -> None:
        """Evict the entry with the earliest expiry when the cache is full."""
        if not self._store:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k][1])
        del self._store[oldest_key]

    async def clear_expired(self) -> int:
        """Remove all expired entries. Returns the number removed."""
        async with self._lock:
            now = time.time()
            expired_keys = [k for k, (_, exp) in self._store.items() if now > exp]
            for k in expired_keys:
                del self._store[k]
            return len(expired_keys)


# Two separate cache instances: one for parser output, one for API data.
parser_cache = TTLCache(max_entries=settings.CACHE_MAX_ENTRIES)
api_cache = TTLCache(max_entries=settings.CACHE_MAX_ENTRIES)


async def get_cached_parser_result(cache_key: str) -> Optional[Any]:
    return await parser_cache.get(cache_key)


async def set_cached_parser_result(cache_key: str, value: Any) -> None:
    await parser_cache.set(cache_key, value, settings.CACHE_TTL_PARSER_SECONDS)


async def get_cached_api_result(cache_key: str) -> Optional[Any]:
    return await api_cache.get(cache_key)


async def set_cached_api_result(cache_key: str, value: Any) -> None:
    await api_cache.set(cache_key, value, settings.CACHE_TTL_API_SECONDS)
