"""Caching system for adapters to improve performance.

This module provides caching mechanisms for expensive operations like:
- Capability discovery
- Tool code generation
- Connectivity testing
"""

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry:
    """Cache entry with TTL support"""

    value: Any
    timestamp: float
    ttl: float

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() > (self.timestamp + self.ttl)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        """Create from dictionary"""
        return cls(**data)


class AdapterCache:
    """In-memory cache for adapter operations"""

    def __init__(self, default_ttl: float = 3600):
        """Initialize cache with default TTL in seconds"""
        self.default_ttl = default_ttl
        self._cache: dict[str, CacheEntry] = {}
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def _generate_key(self, prefix: str, *args: Any, **kwargs: Any) -> str:
        """Generate cache key from arguments"""
        # Create a stable hash from arguments
        key_data = {"args": args, "kwargs": sorted(kwargs.items()) if kwargs else {}}
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()[:16]
        return f"{prefix}:{key_hash}"

    def get(self, key: str) -> Any | None:
        """Get value from cache"""
        entry = self._cache.get(key)
        if entry is None:
            self._stats["misses"] += 1
            return None

        if entry.is_expired():
            del self._cache[key]
            self._stats["evictions"] += 1
            self._stats["misses"] += 1
            return None

        self._stats["hits"] += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        entry = CacheEntry(value=value, timestamp=time.time(), ttl=ttl)
        self._cache[key] = entry

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count"""
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

        for key in expired_keys:
            del self._cache[key]

        self._stats["evictions"] += len(expired_keys)
        return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "entries": len(self._cache),
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }

    def get_or_compute(self, key: str, compute_func: Callable[[], T], ttl: float | None = None) -> T:
        """Get value from cache or compute if not present"""
        value = self.get(key)
        if value is not None:
            return value  # type: ignore[no-any-return]

        # Compute new value
        computed_value = compute_func()
        self.set(key, computed_value, ttl)
        return computed_value


# Global cache instance
_global_cache = AdapterCache()


def get_global_cache() -> AdapterCache:
    """Get the global cache instance"""
    return _global_cache


def cached(
    prefix: str, ttl: float | None = None, cache_instance: AdapterCache | None = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for caching function results

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        cache_instance: Cache instance to use (defaults to global cache)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache = cache_instance or get_global_cache()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key
            cache_key = cache._generate_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result  # type: ignore[no-any-return]

            # Compute and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        # Add cache management methods to function
        wrapper.cache_clear = lambda: cache.clear()  # type: ignore
        wrapper.cache_stats = lambda: cache.get_stats()  # type: ignore
        wrapper.cache_key = lambda *a, **kw: cache._generate_key(prefix, *a, **kw)  # type: ignore

        return wrapper

    return decorator


def cached_method(prefix: str, ttl: float | None = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for caching method results (includes self in key)

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> T:
            # Get cache from self or use global
            cache = getattr(self, "_cache", None) or get_global_cache()

            # Include class name and instance id in key for uniqueness
            instance_key = f"{self.__class__.__name__}:{id(self)}"
            cache_key = cache._generate_key(f"{prefix}:{instance_key}", *args, **kwargs)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result  # type: ignore[no-any-return]

            # Compute and cache result
            result = func(self, *args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


class CacheConfig:
    """Configuration for adapter caching"""

    def __init__(
        self,
        enabled: bool = True,
        default_ttl: float = 3600,  # 1 hour
        discovery_ttl: float = 1800,  # 30 minutes
        generation_ttl: float = 7200,  # 2 hours
        connectivity_ttl: float = 300,  # 5 minutes
        max_entries: int = 1000,
    ):
        self.enabled = enabled
        self.default_ttl = default_ttl
        self.discovery_ttl = discovery_ttl
        self.generation_ttl = generation_ttl
        self.connectivity_ttl = connectivity_ttl
        self.max_entries = max_entries

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "enabled": self.enabled,
            "default_ttl": self.default_ttl,
            "discovery_ttl": self.discovery_ttl,
            "generation_ttl": self.generation_ttl,
            "connectivity_ttl": self.connectivity_ttl,
            "max_entries": self.max_entries,
        }


# Default cache configuration
DEFAULT_CACHE_CONFIG = CacheConfig()


def configure_cache(config: CacheConfig) -> None:
    """Configure global cache settings"""
    global _global_cache
    _global_cache = AdapterCache(config.default_ttl)


def get_cache_config() -> CacheConfig:
    """Get current cache configuration"""
    return DEFAULT_CACHE_CONFIG
