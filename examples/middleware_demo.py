#!/usr/bin/env python3
"""
FastMCP-Factory Comprehensive Middleware Examples

Demonstrates various middleware configuration and usage patterns:
1. Built-in middleware usage (timing, logging, rate_limiting, error_handling)
2. Middleware configuration and parameter tuning
3. Middleware composition and stacking
4. Custom middleware integration
5. Environment-specific middleware configuration strategies

Usage: python middleware_demo.py
"""

import asyncio
import logging
import tempfile
from typing import Any

from mcp_factory.factory import MCPFactory

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main function for comprehensive middleware examples"""
    print("🔧 FastMCP-Factory Comprehensive Middleware Examples")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as temp_workspace:
        factory = MCPFactory(workspace_root=temp_workspace)

        # 1. Basic middleware examples
        await demo_basic_middleware(factory)

        # 2. Production environment middleware stack
        await demo_production_middleware(factory)

        # 3. Custom middleware examples
        await demo_custom_middleware(factory)

        # 4. Enterprise middleware stack demonstration
        await demo_enterprise_middleware(factory)

        # 5. Middleware performance comparison
        await demo_middleware_performance(factory)

        print("\n✨ Middleware examples demonstration completed!")


async def demo_basic_middleware(factory: MCPFactory) -> None:
    """Demonstrate basic middleware usage"""
    print("\n🎯 Basic Middleware Examples")
    print("-" * 30)

    # Basic middleware configuration
    config = {
        "server": {"name": "basic-middleware-server", "instructions": "Basic middleware demonstration server"},
        "runtime": {"transport": "stdio", "log_level": "INFO"},
        "middleware": [
            {
                "type": "timing",
                "enabled": True,
                "config": {
                    "log_level": 20  # INFO level
                },
            },
            {
                "type": "logging",
                "enabled": True,
                "config": {"include_payloads": True, "max_payload_length": 500, "log_level": 20},
            },
        ],
        "tools": {"expose_management_tools": True},
    }

    try:
        server_id = factory.create_server("basic-middleware", config)
        server = factory.get_server(server_id)

        # Add test tools
        @server.tool(name="calculate", description="Simple calculation for middleware testing")
        def calculate(a: int, b: int, operation: str = "add") -> dict[str, Any]:
            """Calculation function for testing middleware"""
            if operation == "add":
                result = a + b
            elif operation == "multiply":
                result = a * b
            else:
                raise ValueError(f"Unsupported operation: {operation}")

            return {
                "operation": operation,
                "operands": [a, b],
                "result": result,
                "middleware_info": "This request was processed through timing and logging middleware",
            }

        print(f"✅ Basic middleware server created successfully: {server.name}")
        print("🔧 Loaded middleware: timing (request timing) + logging (request logging)")
        print("💡 Middleware will record timing and detailed information for each tool call")

        # Note: Actual tool calls need to be made through MCP client
        print("🧮 Tools registered, can be called via MCP client: 'calculate' tool")

    except Exception as e:
        logger.error(f"Basic middleware example failed: {e}")


async def demo_production_middleware(factory: MCPFactory) -> None:
    """Demonstrate production environment middleware stack"""
    print("\n🏭 Production Environment Middleware Stack")
    print("-" * 30)

    # Production environment middleware configuration
    config = {
        "server": {
            "name": "production-middleware-server",
            "instructions": "Production-grade middleware stack demonstration",
        },
        "runtime": {"transport": "stdio", "log_level": "WARNING"},
        "middleware": [
            # 1. Error handling middleware (executed first)
            {
                "type": "error_handling",
                "enabled": True,
                "config": {
                    "include_traceback": False,  # Don't expose stack traces in production
                    "transform_errors": True,
                },
            },
            # 2. Rate limiting middleware
            {
                "type": "rate_limiting",
                "enabled": True,
                "config": {"max_requests_per_second": 10.0, "burst_capacity": 20, "global_limit": True},
            },
            # 3. Performance monitoring middleware
            {
                "type": "timing",
                "enabled": True,
                "config": {
                    "log_level": 30  # WARNING level - only log slow requests
                },
            },
            # 4. Request logging middleware (executed last)
            {
                "type": "logging",
                "enabled": True,
                "config": {
                    "include_payloads": False,  # Don't log payloads in production
                    "max_payload_length": 100,
                    "log_level": 30,  # WARNING level
                },
            },
        ],
        "tools": {
            "expose_management_tools": False  # Hide management tools in production
        },
    }

    try:
        server_id = factory.create_server("production-middleware", config)
        server = factory.get_server(server_id)

        # Add business tools
        @server.tool(name="process_data", description="Data processing with production middleware")
        def process_data(data: list[int], operation: str = "sum") -> dict[str, Any]:
            """Data processing function"""
            if operation == "sum":
                result: int | float = sum(data)
            elif operation == "average":
                result = sum(data) / len(data) if data else 0.0
            else:
                raise ValueError(f"Invalid operation: {operation}")

            return {
                "operation": operation,
                "data_size": len(data),
                "result": result,
                "processed_with": "production middleware stack",
            }

        print(f"✅ Production environment server created successfully: {server.name}")
        print("🔧 Middleware stack (execution order):")
        print("   1. error_handling - Error handling and transformation")
        print("   2. rate_limiting - Rate limiting (10 req/s)")
        print("   3. timing - Performance monitoring")
        print("   4. logging - Request logging (WARNING level)")
        print("🔒 Security configuration: No stack trace exposure, no sensitive payload logging")

        # Test call example:
        # test_data = [1, 2, 3, 4, 5]
        # result = process_data(test_data, "average")
        # print(f"📊 Data processing result: {result['result']}")
        print("📊 Tools registered, can be called via MCP client: 'process_data' tool")

    except Exception as e:
        logger.error(f"Production environment middleware example failed: {e}")


async def demo_custom_middleware(factory: MCPFactory) -> None:
    """Demonstrate custom middleware integration"""
    print("\n🛠️ Custom Middleware Integration")
    print("-" * 30)

    # Custom middleware configuration
    config = {
        "server": {"name": "custom-middleware-server", "instructions": "Custom middleware integration demonstration"},
        "runtime": {"transport": "stdio", "log_level": "INFO"},
        "middleware": [
            # Built-in middleware
            {"type": "timing", "enabled": True, "config": {"log_level": 20}},
            # Custom middleware example
            {
                "type": "custom",
                "enabled": True,
                "class": "examples.custom_middleware.AuthenticationMiddleware",
                "config": {"api_keys": ["demo-key-1", "demo-key-2"], "allow_anonymous": True},
            },
        ],
        "tools": {"expose_management_tools": True},
    }

    try:
        server_id = factory.create_server("custom-middleware", config)
        server = factory.get_server(server_id)

        @server.tool(name="secure_operation", description="Secure operation with custom middleware")
        def secure_operation(operation_id: str) -> dict[str, Any]:
            """Secure operation that requires custom middleware authentication"""
            return {
                "operation_id": operation_id,
                "status": "completed",
                "message": "Operation completed successfully",
                "security_note": "This operation was processed through custom authentication middleware",
            }

        print(f"✅ Custom middleware server created successfully: {server.name}")
        print("🔧 Integrated: timing (built-in) + AuthenticationMiddleware (custom)")
        print("💡 Custom middleware capabilities:")
        print("   - Authentication and authorization ✅")
        print("   - Audit logging")
        print("   - Business rule validation")
        print("   - Caching strategies")
        print("📖 See custom_middleware.py for more custom middleware implementations")

        # Test call
        # result = secure_operation("OP-12345")
        # print(f"🔐 Secure operation result: {result['status']}")
        print("🔐 Tools registered, can be called via MCP client: 'secure_operation' tool")

    except Exception as e:
        logger.error(f"Custom middleware example failed: {e}")


async def demo_enterprise_middleware(factory: MCPFactory) -> None:
    """Demonstrate enterprise-grade middleware stack"""
    print("\n🏢 Enterprise-Grade Middleware Stack Demonstration")
    print("-" * 30)

    # Enterprise-grade complete middleware configuration
    config = {
        "server": {
            "name": "enterprise-middleware-server",
            "instructions": "Enterprise-grade middleware stack with custom middleware",
        },
        "runtime": {"transport": "stdio", "log_level": "INFO"},
        "middleware": [
            # 1. Authentication middleware (executed first)
            {
                "type": "custom",
                "enabled": True,
                "class": "examples.custom_middleware.AuthenticationMiddleware",
                "config": {
                    "api_keys": ["enterprise-key-1", "enterprise-key-2"],
                    "header_name": "X-API-Key",
                    "allow_anonymous": False,
                },
            },
            # 2. Audit middleware
            {
                "type": "custom",
                "enabled": True,
                "class": "examples.custom_middleware.AuditMiddleware",
                "config": {
                    "log_file": "/tmp/enterprise_audit.log",
                    "include_payloads": True,
                    "sensitive_fields": ["password", "token", "api_key"],
                },
            },
            # 3. Cache middleware
            {
                "type": "custom",
                "enabled": True,
                "class": "examples.custom_middleware.CacheMiddleware",
                "config": {
                    "cache_ttl": 300,  # 5 minutes
                    "max_cache_size": 100,
                    "cacheable_methods": ["get_tools", "get_resource"],
                },
            },
            # 4. Built-in middleware
            {
                "type": "error_handling",
                "enabled": True,
                "config": {"include_traceback": False, "transform_errors": True},
            },
            {"type": "timing", "enabled": True, "config": {"log_level": 20}},
        ],
        "tools": {"expose_management_tools": True},
    }

    try:
        server_id = factory.create_server("enterprise-middleware", config)
        server = factory.get_server(server_id)

        # Add enterprise business tools
        @server.tool(name="enterprise_operation", description="Enterprise operation with full middleware stack")
        def enterprise_operation(operation_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
            """Enterprise-grade operation processed through complete middleware stack"""
            operations = {
                "user_info": {"user_id": "12345", "role": "admin", "permissions": ["read", "write"]},
                "system_status": {"status": "healthy", "uptime": "99.9%", "services": 12},
                "audit_report": {"total_requests": 1000, "errors": 2, "avg_response_time": "120ms"},
            }

            result = operations.get(operation_type, {"error": "Unknown operation"})

            return {
                "operation": operation_type,
                "result": result,
                "processed_by": "enterprise middleware stack",
                "middleware_chain": [
                    "AuthenticationMiddleware",
                    "AuditMiddleware",
                    "CacheMiddleware",
                    "ErrorHandlingMiddleware",
                    "TimingMiddleware",
                ],
            }

        print(f"✅ Enterprise-grade server created successfully: {server.name}")
        print("🔧 Complete middleware stack (execution order):")
        print("   1. 🔐 AuthenticationMiddleware - API key verification")
        print("   2. 📝 AuditMiddleware - Security audit logging")
        print("   3. 🚀 CacheMiddleware - Intelligent response caching")
        print("   4. ⚠️  ErrorHandlingMiddleware - Error handling")
        print("   5. ⏱️  TimingMiddleware - Performance monitoring")
        print("💼 Enterprise capabilities:")
        print("   - Authentication and authorization")
        print("   - Complete audit trail")
        print("   - Performance optimization caching")
        print("   - Graceful error handling")
        print("   - Detailed performance monitoring")
        print("🔍 Check /tmp/enterprise_audit.log for audit logs")

    except Exception as e:
        logger.error(f"Enterprise middleware example failed: {e}")


async def demo_middleware_performance(factory: MCPFactory) -> None:
    """Demonstrate middleware performance impact"""
    print("\n⚡ Middleware Performance Comparison")
    print("-" * 30)

    # No middleware configuration
    no_middleware_config = {
        "server": {
            "name": "no-middleware-server",
            "instructions": "Server without middleware for performance comparison",
        },
        "runtime": {"transport": "stdio"},
        "tools": {"expose_management_tools": True},
    }

    # Full middleware configuration
    full_middleware_config = {
        "server": {"name": "full-middleware-server", "instructions": "Server with full middleware stack"},
        "runtime": {"transport": "stdio"},
        "middleware": [
            {"type": "error_handling", "enabled": True},
            {"type": "rate_limiting", "enabled": True, "config": {"max_requests_per_second": 100.0}},
            {"type": "timing", "enabled": True},
            {"type": "logging", "enabled": True, "config": {"include_payloads": False}},
        ],
        "tools": {"expose_management_tools": True},
    }

    try:
        # Create two servers for comparison
        no_middleware_id = factory.create_server("no-middleware", no_middleware_config)
        full_middleware_id = factory.create_server("full-middleware", full_middleware_config)

        no_middleware_server = factory.get_server(no_middleware_id)
        full_middleware_server = factory.get_server(full_middleware_id)

        # Add identical test tools to both servers
        def add_test_tool(server: Any, server_type: str) -> None:
            @server.tool(name=f"benchmark_{server_type}", description=f"Benchmark tool for {server_type}")
            def benchmark_tool(iterations: int = 1000) -> dict[str, Any]:
                """Benchmark testing tool"""
                total = 0
                for i in range(iterations):
                    total += i
                return {"iterations": iterations, "result": total, "server_type": server_type}

        add_test_tool(no_middleware_server, "no_middleware")
        add_test_tool(full_middleware_server, "full_middleware")

        print("✅ Performance comparison servers created successfully")
        print("📊 Configuration comparison:")
        print(f"   - No middleware server: {no_middleware_server.name}")
        print(f"   - Full middleware server: {full_middleware_server.name}")
        print("💡 Actual performance testing requires calls through MCP client")
        print("🔧 Middleware overhead is typically small, but provides important functionality:")
        print("   - Error handling and recovery")
        print("   - Security protection and rate limiting")
        print("   - Monitoring and logging")
        print("   - Request tracing and debugging")

    except Exception as e:
        logger.error(f"Performance comparison example failed: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Examples stopped")
    except Exception as e:
        logger.error(f"Example execution error: {e}")
        raise
