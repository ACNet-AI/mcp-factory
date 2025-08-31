"""Async utilities for adapter operations

This module provides utilities for:
- Concurrent processing
- Timeout handling
- Retry mechanisms
- Parallel processing utilities
"""

import asyncio
import concurrent.futures
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


class AsyncAdapter:
    """Mixin class for async adapter operations"""

    def __init__(self) -> None:
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    async def run_in_executor(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
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

    def cleanup(self) -> None:
        """Cleanup executor"""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=True)


class ConcurrentDiscovery:
    """Utility for concurrent capability discovery"""

    @staticmethod
    async def discover_multiple_sources(adapters: list[Any], max_concurrency: int = 5) -> dict[str, list[Any]]:
        """Discover capabilities from multiple adapters concurrently"""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def discover_single(adapter: Any) -> tuple[str, list[Any]]:
            async with semaphore:
                try:
                    # Run sync discovery in executor
                    loop = asyncio.get_event_loop()
                    capabilities = await loop.run_in_executor(None, adapter.discover_capabilities)
                    return adapter.name, capabilities
                except Exception:
                    return adapter.name, []

        tasks = [discover_single(adapter) for adapter in adapters]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and build result dict
        result_dict = {}
        for result in results:
            if isinstance(result, tuple):
                name, capabilities = result
                result_dict[name] = capabilities

        return result_dict


async def timeout_wrapper(coro: Awaitable[T], timeout: float) -> T:
    """Wrap coroutine with timeout"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError as e:
        raise TimeoutError(f"Operation timed out after {timeout}s") from e


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]], *args: Any, max_retries: int = 3, base_delay: float = 1.0, **kwargs: Any
) -> T:
    """Retry async function with exponential backoff"""
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2**attempt)
                await asyncio.sleep(delay)
            else:
                break

    if last_exception:
        raise last_exception
    raise RuntimeError("Retry failed without exception")


def run_sync_in_async(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run sync function in async context"""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If we're already in an async context, use executor
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(func, *args, **kwargs)
        return future.result()
    else:
        # If not in async context, just run directly
        return func(*args, **kwargs)


class PerformanceMonitor:
    """Simple performance monitoring for adapters"""

    def __init__(self) -> None:
        self._metrics: dict[str, list[float]] = {}

    def record_time(self, operation: str, duration: float) -> None:
        """Record operation duration"""
        if operation not in self._metrics:
            self._metrics[operation] = []
        self._metrics[operation].append(duration)

    def get_stats(self, operation: str) -> dict[str, float]:
        """Get statistics for an operation"""
        if operation not in self._metrics:
            return {}

        times = self._metrics[operation]
        return {
            "count": len(times),
            "total": sum(times),
            "average": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
        }

    def get_all_stats(self) -> dict[str, dict[str, float]]:
        """Get all operation statistics"""
        return {op: self.get_stats(op) for op in self._metrics}


def performance_tracked(operation_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to track function performance"""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            import time

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                # Could integrate with monitoring system here
                print(f"{operation_name} took {duration:.3f}s")

        return wrapper

    return decorator


class AdapterPool:
    """Simple adapter pool for reuse"""

    def __init__(self, max_size: int = 10) -> None:
        self.max_size = max_size
        self._pool: list[Any] = []
        self._in_use: set[Any] = set()

    def get_adapter(self, adapter_factory: Callable[[], Any]) -> Any:
        """Get adapter from pool or create new one"""
        if self._pool:
            adapter = self._pool.pop()
            self._in_use.add(adapter)
            return adapter
        else:
            adapter = adapter_factory()
            self._in_use.add(adapter)
            return adapter

    def return_adapter(self, adapter: Any) -> None:
        """Return adapter to pool"""
        if adapter in self._in_use:
            self._in_use.remove(adapter)
            if len(self._pool) < self.max_size:
                self._pool.append(adapter)

    def cleanup(self) -> None:
        """Cleanup all adapters"""
        for adapter in self._pool + list(self._in_use):
            if hasattr(adapter, "cleanup"):
                adapter.cleanup()
        self._pool.clear()
        self._in_use.clear()
