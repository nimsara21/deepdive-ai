import hashlib
import time
from dataclasses import dataclass
from typing import Optional

from .state import AgentState


@dataclass
class CacheEntry:
    state: AgentState
    timestamp: float


class ResearchCache:
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 100):
        """
        Args:
            ttl_seconds: Time-to-live for cached entries (default 1 hour)
            max_size: Maximum number of cached entries (FIFO eviction when exceeded)
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: dict[str, CacheEntry] = {}

    def _hash_query(self, query: str) -> str:
        """Create a deterministic hash of the query for use as cache key."""
        normalized = query.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, query: str) -> Optional[AgentState]:
        """Retrieve cached result if it exists and hasn't expired."""
        key = self._hash_query(query)

        if key not in self._cache:
            return None

        entry = self._cache[key]
        age = time.time() - entry.timestamp

        if age > self.ttl_seconds:
            del self._cache[key]
            return None

        return entry.state

    def set(self, query: str, state: AgentState) -> None:
        """Store a research result in the cache."""
        key = self._hash_query(query)

        # Evict oldest entry if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].timestamp)
            del self._cache[oldest_key]

        self._cache[key] = CacheEntry(state=state, timestamp=time.time())

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def stats(self) -> dict:
        """Return cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
        }
