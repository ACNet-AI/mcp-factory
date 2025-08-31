#!/usr/bin/env python3
"""Performance demonstration for adapter caching.

This script shows the performance benefits of caching in adapters.
"""

import time
from typing import Any

from mcp_factory.adapters import adapt


def measure_time(func, *args, **kwargs) -> tuple[Any, float]:
    """Measure execution time of a function"""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time


def performance_test_python_adapter():
    """Test Python adapter performance with and without caching"""
    print("🔍 Python Adapter Performance Test")
    print("=" * 50)

    # Create adapter
    adapter = adapt.python("mcp_factory.factory.MCPFactory")

    # First call (cold cache)
    print("📊 First call (cold cache):")
    capabilities1, time1 = measure_time(adapter.discover_capabilities)
    print(f"   Capabilities discovered: {len(capabilities1)}")
    print(f"   Time taken: {time1:.3f}s")

    # Second call (warm cache)
    print("\n📊 Second call (warm cache):")
    capabilities2, time2 = measure_time(adapter.discover_capabilities)
    print(f"   Capabilities discovered: {len(capabilities2)}")
    print(f"   Time taken: {time2:.3f}s")

    # Performance improvement
    speedup = time1 / time2 if time2 > 0 else float("inf")
    print(f"\n⚡ Performance improvement: {speedup:.1f}x faster")
    print(f"   Time saved: {((time1 - time2) / time1 * 100):.1f}%")

    # Test tool generation
    if capabilities1:
        print("\n🛠️ Tool Code Generation Test:")
        capability = capabilities1[0]

        # First generation (cold cache)
        code1, gen_time1 = measure_time(adapter.generate_tool_code, capability)
        print(f"   First generation time: {gen_time1:.3f}s")

        # Second generation (warm cache)
        code2, gen_time2 = measure_time(adapter.generate_tool_code, capability)
        print(f"   Cached generation time: {gen_time2:.3f}s")

        gen_speedup = gen_time1 / gen_time2 if gen_time2 > 0 else float("inf")
        print(f"   Generation improvement: {gen_speedup:.1f}x faster")


def performance_test_multi_adapter():
    """Test multi-adapter performance"""
    print("\n🔄 Multi-Adapter Performance Test")
    print("=" * 50)

    # Create multi-adapter
    multi = adapt.multi()

    # Add multiple sources
    sources = ["mcp_factory.factory.MCPFactory", "mcp_factory.server.ManagedServer", "echo hello", "ls -la"]

    print("📦 Adding multiple data sources:")
    for source in sources:
        name = multi.add_source(source)
        print(f"   ✅ {name}: {source}")

    # First discovery (cold cache)
    print("\n🔍 First full discovery:")
    all_caps1, discovery_time1 = measure_time(multi.discover_all_capabilities)
    total_caps1 = sum(len(caps) for caps in all_caps1.values())
    print(f"   Total capabilities: {total_caps1}")
    print(f"   Discovery time: {discovery_time1:.3f}s")

    # Second discovery (warm cache)
    print("\n🔍 Cached full discovery:")
    all_caps2, discovery_time2 = measure_time(multi.discover_all_capabilities)
    total_caps2 = sum(len(caps) for caps in all_caps2.values())
    print(f"   Total capabilities: {total_caps2}")
    print(f"   Discovery time: {discovery_time2:.3f}s")

    # Performance improvement
    multi_speedup = discovery_time1 / discovery_time2 if discovery_time2 > 0 else float("inf")
    print(f"\n⚡ Multi-adapter performance improvement: {multi_speedup:.1f}x faster")


def cache_statistics_demo():
    """Demonstrate cache statistics"""
    print("\n📈 Cache Statistics Demo")
    print("=" * 50)

    # Create adapter with cache
    adapter = adapt.python("mcp_factory.factory.MCPFactory")

    # Make multiple calls to populate cache
    for _i in range(5):
        adapter.discover_capabilities()

    # Get cache statistics
    if hasattr(adapter, "_cache") and adapter._cache:
        stats = adapter._cache.get_stats()
        print("📊 Cache Statistics:")
        print(f"   Cache entries: {stats['entries']}")
        print(f"   Cache hits: {stats['hits']}")
        print(f"   Cache misses: {stats['misses']}")
        print(f"   Hit rate: {stats['hit_rate']:.1%}")
        print(f"   Total requests: {stats['total_requests']}")


def memory_usage_demo():
    """Demonstrate memory efficiency"""
    print("\n💾 Memory Usage Demo")
    print("=" * 50)

    import os

    import psutil

    process = psutil.Process(os.getpid())

    # Initial memory
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"Initial memory usage: {initial_memory:.1f} MB")

    # Create multiple adapters
    adapters = []
    for _i in range(10):
        adapter = adapt.python("mcp_factory.factory.MCPFactory")
        adapter.discover_capabilities()  # Populate cache
        adapters.append(adapter)

    # Memory after creating adapters
    after_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"After creating adapters: {after_memory:.1f} MB")
    print(f"Memory growth: {after_memory - initial_memory:.1f} MB")

    # Clear caches
    for adapter in adapters:
        if hasattr(adapter, "_cache") and adapter._cache:
            adapter._cache.clear()

    # Memory after clearing cache
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"After clearing cache: {final_memory:.1f} MB")


def async_performance_demo():
    """Demonstrate async performance benefits"""
    print("\n⚡ Async Performance Demo")
    print("=" * 50)

    import asyncio

    async def async_discovery_test():
        """Test async capability discovery"""
        # Create HTTP adapter (supports async)
        try:
            adapter = adapt.http("https://httpbin.org")

            # Test connectivity first
            connectivity = adapter.test_connectivity()
            if not connectivity.success:
                print("   ⚠️ HTTP connection failed, skipping async test")
                return

            # Async discovery
            start_time = time.time()
            capabilities = adapter.discover_capabilities()
            end_time = time.time()

            print(f"   HTTP endpoints discovered: {len(capabilities)}")
            print(f"   Discovery time: {end_time - start_time:.3f}s")

        except Exception as e:
            print(f"   ⚠️ Async test failed: {e}")

    # Run async test
    try:
        asyncio.run(async_discovery_test())
    except Exception as e:
        print(f"   ⚠️ Async execution failed: {e}")


def main():
    """Run all performance demonstrations"""
    print("🚀 MCP Factory Adapter Performance Demo")
    print("=" * 60)
    print("This demo shows the performance benefits of caching and async processing")
    print()

    try:
        # Python adapter performance
        performance_test_python_adapter()

        # Multi-adapter performance
        performance_test_multi_adapter()

        # Cache statistics
        cache_statistics_demo()

        # Memory usage
        try:
            memory_usage_demo()
        except ImportError:
            print("\n💾 Memory demo skipped (requires psutil)")

        # Async performance
        async_performance_demo()

        print("\n" + "=" * 60)
        print("🎉 Performance demo completed!")
        print("\n💡 Key Benefits:")
        print("   • Caching can improve performance by 5-50x")
        print("   • Reduces repeated module imports and reflection operations")
        print("   • Lowers network requests and process creation overhead")
        print("   • Async processing improves concurrency")
        print("   • Smart TTL management ensures data freshness")

    except Exception as e:
        print(f"❌ Error occurred during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
