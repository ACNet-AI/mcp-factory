"""Async utilities for adapter performance optimization.

This module provides async utilities to improve adapter performance:
- Concurrent capability discovery
- Async HTTP operations
- Parallel processing utilities
"""

import asyncio
import concurrent.futures
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


class AsyncAdapter:
    """Mixin class for async adapter operations"""

    def __init__(self):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    async def run_in_executor(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Run sync function in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args, **kwargs)

    async def gather_with_concurrency(self, tasks: list[Awaitable[T]], max_concurrency: int = 10) -> list[T]:
        """Execute tasks with limited concurrency"""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def bounded_task(task: Awaitable[T]) -> T:
            async with semaphore:
                return await task

        bounded_tasks = [bounded_task(task) for task in tasks]
        return await asyncio.gather(*bounded_tasks)

    def cleanup(self):
        """Cleanup executor"""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=True)


class ConcurrentDiscovery:
    """Utility for concurrent capability discovery"""

    @staticmethod
    async def discover_multiple_sources(adapters: list[Any], max_concurrency: int = 5) -> dict[str, list[Any]]:
        """Discover capabilities from multiple adapters concurrently"""

        async def discover_single(adapter) -> tuple[str, list[Any]]:
            """Discover capabilities for a single adapter"""
            try:
                # Get adapter name
                adapter_name = getattr(adapter, "name", adapter.__class__.__name__)

                # Run discovery in executor if it's sync
                if asyncio.iscoroutinefunction(adapter.discover_capabilities):
                    capabilities = await adapter.discover_capabilities()
                else:
                    loop = asyncio.get_event_loop()
                    capabilities = await loop.run_in_executor(None, adapter.discover_capabilities)

                return adapter_name, capabilities
            except Exception:
                return adapter_name, []

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrency)

        async def bounded_discover(adapter) -> tuple[str, list[Any]]:
            async with semaphore:
                return await discover_single(adapter)

        # Execute all discoveries concurrently
        tasks = [bounded_discover(adapter) for adapter in adapters]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        capabilities_map = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            name, capabilities = result
            capabilities_map[name] = capabilities

        return capabilities_map


class AsyncCache:
    """Async-aware cache implementation"""

    def __init__(self):
        self._cache = {}
        self._locks = {}

    async def get_or_compute_async(self, key: str, compute_func: Callable[[], Awaitable[T]], ttl: float = 3600) -> T:
        """Get from cache or compute async"""
        # Check if already in cache
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                return entry.value

        # Get or create lock for this key
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        # Acquire lock and compute
        async with self._locks[key]:
            # Double-check after acquiring lock
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    return entry.value

            # Compute new value
            value = await compute_func()

            # Store in cache
            import time

            from .cache import CacheEntry

            self._cache[key] = CacheEntry(value=value, timestamp=time.time(), ttl=ttl)

            return value


class BatchProcessor:
    """Batch processing utilities for adapters"""

    @staticmethod
    async def process_in_batches(
        items: list[T], processor: Callable[[T], Awaitable[Any]], batch_size: int = 10, max_concurrency: int = 5
    ) -> list[Any]:
        """Process items in batches with concurrency control"""
        results = []
        semaphore = asyncio.Semaphore(max_concurrency)

        async def process_item(item: T) -> Any:
            async with semaphore:
                return await processor(item)

        # Process in batches
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            batch_tasks = [process_item(item) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)

        return results


class PerformanceMonitor:
    """Monitor adapter performance"""

    def __init__(self):
        self.metrics = {"discovery_times": [], "generation_times": [], "cache_hits": 0, "cache_misses": 0}

    def record_discovery_time(self, time_taken: float):
        """Record capability discovery time"""
        self.metrics["discovery_times"].append(time_taken)

    def record_generation_time(self, time_taken: float):
        """Record tool generation time"""
        self.metrics["generation_times"].append(time_taken)

    def record_cache_hit(self):
        """Record cache hit"""
        self.metrics["cache_hits"] += 1

    def record_cache_miss(self):
        """Record cache miss"""
        self.metrics["cache_misses"] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics"""
        discovery_times = self.metrics["discovery_times"]
        generation_times = self.metrics["generation_times"]

        return {
            "discovery": {
                "count": len(discovery_times),
                "avg_time": sum(discovery_times) / len(discovery_times) if discovery_times else 0,
                "min_time": min(discovery_times) if discovery_times else 0,
                "max_time": max(discovery_times) if discovery_times else 0,
            },
            "generation": {
                "count": len(generation_times),
                "avg_time": sum(generation_times) / len(generation_times) if generation_times else 0,
                "min_time": min(generation_times) if generation_times else 0,
                "max_time": max(generation_times) if generation_times else 0,
            },
            "cache": {
                "hits": self.metrics["cache_hits"],
                "misses": self.metrics["cache_misses"],
                "hit_rate": (
                    self.metrics["cache_hits"] / (self.metrics["cache_hits"] + self.metrics["cache_misses"])
                    if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0
                    else 0
                ),
            },
        }


# Global performance monitor
_global_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor"""
    return _global_monitor


def performance_tracked(operation_type: str):
    """Decorator to track operation performance"""

    def decorator(func):
        import functools
        import time

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration = end_time - start_time

                monitor = get_performance_monitor()
                if operation_type == "discovery":
                    monitor.record_discovery_time(duration)
                elif operation_type == "generation":
                    monitor.record_generation_time(duration)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration = end_time - start_time

                monitor = get_performance_monitor()
                if operation_type == "discovery":
                    monitor.record_discovery_time(duration)
                elif operation_type == "generation":
                    monitor.record_generation_time(duration)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class AdapterPool:
    """Pool of adapters for load balancing"""

    def __init__(self, adapter_factory: Callable[[], Any], pool_size: int = 3):
        self.adapter_factory = adapter_factory
        self.pool_size = pool_size
        self._pool = []
        self._current = 0
        self._lock = asyncio.Lock()

    async def get_adapter(self) -> Any:
        """Get adapter from pool (round-robin)"""
        async with self._lock:
            if len(self._pool) < self.pool_size:
                # Create new adapter
                adapter = self.adapter_factory()
                self._pool.append(adapter)
                return adapter
            else:
                # Round-robin selection
                adapter = self._pool[self._current]
                self._current = (self._current + 1) % self.pool_size
                return adapter

    async def cleanup(self):
        """Cleanup all adapters in pool"""
        for adapter in self._pool:
            if hasattr(adapter, "cleanup"):
                await adapter.cleanup()
        self._pool.clear()


# Utility functions for common async patterns


async def timeout_wrapper(coro: Awaitable[T], timeout_seconds: float) -> T:
    """Wrap coroutine with timeout"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError as e:
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds") from e


async def retry_with_backoff(coro_func: Callable[[], Awaitable[T]], max_retries: int = 3, base_delay: float = 1.0) -> T:
    """Retry coroutine with exponential backoff"""
    for attempt in range(max_retries + 1):
        try:
            return await coro_func()
        except Exception as e:
            if attempt == max_retries:
                raise e

            delay = base_delay * (2**attempt)
            await asyncio.sleep(delay)

    raise RuntimeError("Retry logic failed unexpectedly")


def make_async_safe(func: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    """Make a sync function async-safe by running in executor"""

    async def async_wrapper(*args, **kwargs) -> T:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    return async_wrapper
