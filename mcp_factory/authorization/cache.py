"""
Permission check cache system

Provides high-performance permission check caching to reduce duplicate permission verification overhead
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry"""

    result: bool
    timestamp: float
    hit_count: int = 0


class PermissionCache:
    """Permission check cache"""

    def __init__(self, ttl: int = 300, max_size: int = 10000):
        """
        Initialize permission cache

        Args:
            ttl: Cache time-to-live (seconds), default 5 minutes
            max_size: Maximum cache entries, default 10000
        """
        self.ttl = ttl
        self.max_size = max_size
        self.cache: dict[str, CacheEntry] = {}
        self.lock = RLock()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}

        logger.info(f"Permission cache initialized with TTL={ttl}s, max_size={max_size}")

    def _generate_key(self, user_id: str, permission: str, context: dict[str, Any] | None = None) -> str:
        """Generate cache key"""
        if context:
            context_str = "|".join(f"{k}:{v}" for k, v in sorted(context.items()))
            return f"{user_id}:{permission}:{context_str}"
        return f"{user_id}:{permission}"

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired"""
        return time.time() - entry.timestamp > self.ttl

    def _evict_expired(self) -> None:
        """Clean up expired cache entries"""
        current_time = time.time()
        expired_keys = [key for key, entry in self.cache.items() if current_time - entry.timestamp > self.ttl]

        for key in expired_keys:
            del self.cache[key]
            self.stats["evictions"] += 1

        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired cache entries")

    def _evict_lru(self) -> None:
        """LRU eviction strategy"""
        if len(self.cache) >= self.max_size:
            # Find the least recently used entry
            lru_key = min(self.cache.keys(), key=lambda k: (self.cache[k].hit_count, self.cache[k].timestamp))
            del self.cache[lru_key]
            self.stats["evictions"] += 1
            logger.debug(f"LRU evicted cache entry: {lru_key}")

    def get(self, user_id: str, permission: str, context: dict[str, Any] | None = None) -> bool | None:
        """
        Get cached permission check result

        Args:
            user_id: User ID
            permission: Permission string
            context: Context information

        Returns:
            Cached result, or None if cache miss or expired
        """
        cache_key = self._generate_key(user_id, permission, context)

        with self.lock:
            entry = self.cache.get(cache_key)

            if entry is None:
                self.stats["misses"] += 1
                return None

            if self._is_expired(entry):
                del self.cache[cache_key]
                self.stats["misses"] += 1
                self.stats["evictions"] += 1
                return None

            # Update access statistics
            entry.hit_count += 1
            self.stats["hits"] += 1

            logger.debug(f"Cache hit for {cache_key}: {entry.result}")
            return entry.result

    def set(self, user_id: str, permission: str, result: bool, context: dict[str, Any] | None = None) -> None:
        """
        Set permission check result to cache

        Args:
            user_id: User ID
            permission: Permission string
            result: Permission check result
            context: Context information
        """
        cache_key = self._generate_key(user_id, permission, context)

        with self.lock:
            # Clean up expired entries
            self._evict_expired()

            # LRU eviction
            self._evict_lru()

            # Add new entry
            self.cache[cache_key] = CacheEntry(result=result, timestamp=time.time(), hit_count=0)

            logger.debug(f"Cache set for {cache_key}: {result}")

    def invalidate_user(self, user_id: str) -> None:
        """
        Clear all cache entries for a specific user

        Args:
            user_id: User ID
        """
        with self.lock:
            keys_to_remove = [key for key in self.cache.keys() if key.startswith(f"{user_id}:")]

            for key in keys_to_remove:
                del self.cache[key]
                self.stats["evictions"] += 1

            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for user {user_id}")

    def invalidate_permission(self, permission: str) -> None:
        """
        Clear all cache entries for a specific permission

        Args:
            permission: Permission string
        """
        with self.lock:
            keys_to_remove = [key for key in self.cache.keys() if f":{permission}" in key]

            for key in keys_to_remove:
                del self.cache[key]
                self.stats["evictions"] += 1

            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for permission {permission}")

    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            self.stats["evictions"] += count
            logger.info(f"Cleared all {count} cache entries")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics information"""
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

            return {
                "cache_size": len(self.cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "hit_rate": hit_rate,
                "evictions": self.stats["evictions"],
                "total_requests": total_requests,
            }

    def get_cache_info(self) -> dict[str, Any]:
        """Get detailed cache information (for debugging)"""
        with self.lock:
            current_time = time.time()

            cache_info = {}
            for key, entry in self.cache.items():
                age = current_time - entry.timestamp
                cache_info[key] = {
                    "result": entry.result,
                    "age_seconds": age,
                    "hit_count": entry.hit_count,
                    "expired": age > self.ttl,
                }

            return cache_info


# Global cache instance
_global_permission_cache: PermissionCache | None = None


def get_permission_cache() -> PermissionCache:
    """Get global permission cache instance"""
    global _global_permission_cache

    if _global_permission_cache is None:
        _global_permission_cache = PermissionCache()

    return _global_permission_cache


def configure_permission_cache(ttl: int = 300, max_size: int = 10000) -> None:
    """Configure global permission cache"""
    global _global_permission_cache
    _global_permission_cache = PermissionCache(ttl=ttl, max_size=max_size)
    logger.info(f"Global permission cache configured with TTL={ttl}s, max_size={max_size}")


# Cache decorator
def cached_permission_check(cache: PermissionCache | None = None) -> Callable:
    """Permission check cache decorator"""

    def decorator(func: Callable) -> Callable:
        def wrapper(user_id: str, permission: str, *args: Any, **kwargs: Any) -> Any:
            permission_cache = cache or get_permission_cache()

            # Try to get from cache
            cached_result = permission_cache.get(user_id, permission)
            if cached_result is not None:
                return cached_result

            # Execute actual check
            result = func(user_id, permission, *args, **kwargs)

            # Cache result
            permission_cache.set(user_id, permission, result)

            return result

        return wrapper

    return decorator
