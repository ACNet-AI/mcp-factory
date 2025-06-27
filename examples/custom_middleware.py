#!/usr/bin/env python3
"""
Custom Middleware Implementation Examples for User Projects

This file demonstrates how users can implement and use custom middleware in their own projects.
Custom middleware can be placed anywhere in the project as long as it can be imported by Python.

The middleware in this file can be used in two ways:
1. Direct import and use in user projects
2. Reference configuration in mcp-factory configuration files

Examples:
- AuthenticationMiddleware: API key authentication
- AuditMiddleware: Security audit logging
- CacheMiddleware: Response caching
"""

import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================================
# User project custom middleware implementations
# ============================================================================


class AuthenticationMiddleware:
    """Identity Validation Middleware

    This is a real-world enterprise middleware example used to validate API keys
    """

    def __init__(
        self,
        api_keys: list[str] | None = None,
        header_name: str = "X-API-Key",
        allow_anonymous: bool = False,
        **config: Any
    ) -> None:
        self.api_keys = set(api_keys or [])
        self.header_name = header_name
        self.allow_anonymous = allow_anonymous
        self.config = config
        logger.info(f"AuthenticationMiddleware initialized: {len(self.api_keys)} keys, anonymous={allow_anonymous}")

    async def __call__(self, request: Any, call_next: Any) -> Any:
        """Validate the API key"""
        # Get API key
        api_key = getattr(request, "headers", {}).get(self.header_name)

        # Check if authentication is required
        if not self.allow_anonymous and not api_key:
            logger.warning(f"Missing API key in header: {self.header_name}")
            raise ValueError(f"Missing {self.header_name} header")

        # Validate API key
        if api_key and api_key not in self.api_keys:
            logger.warning(f"Invalid API key: {api_key[:8]}...")
            raise ValueError("Invalid API key")

        # Add user information to request
        if api_key:
            request.user_id = hashlib.md5(api_key.encode()).hexdigest()[:8]
            logger.info(f"Authenticated user: {request.user_id}")

        return await call_next(request)


class AuditMiddleware:
    """Audit Middleware

    Records all detailed information about API calls, used for compliance and security audits
    """

    def __init__(
        self,
        log_file: str = "audit.log",
        include_payloads: bool = False,
        sensitive_fields: list[str] | None = None,
        **config: Any
    ) -> None:
        self.log_file = log_file
        self.include_payloads = include_payloads
        self.sensitive_fields = set(sensitive_fields or ["password", "token", "key", "secret"])
        self.config = config

        # Set up audit logging
        self.audit_logger = logging.getLogger("audit")
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        self.audit_logger.addHandler(handler)
        self.audit_logger.setLevel(logging.INFO)

        logger.info(f"AuditMiddleware initialized: log_file={log_file}")

    def _sanitize_data(self, data: Any) -> Any:
        """Clean sensitive data"""
        if isinstance(data, dict):
            return {
                key: "***REDACTED***" if key.lower() in self.sensitive_fields else self._sanitize_data(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data

    async def __call__(self, request: Any, call_next: Any) -> Any:
        """Record audit information"""
        start_time = time.time()
        request_id = getattr(request, "id", f"req_{int(time.time())}")
        user_id = getattr(request, "user_id", "anonymous")
        method = getattr(request, "method", "unknown")

        # Record request start
        audit_data = {
            "event": "request_start",
            "request_id": request_id,
            "user_id": user_id,
            "method": method,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self.include_payloads:
            params = getattr(request, "params", {})
            audit_data["params"] = self._sanitize_data(params)

        self.audit_logger.info(json.dumps(audit_data))

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Record successful response
            audit_data = {
                "event": "request_success",
                "request_id": request_id,
                "user_id": user_id,
                "method": method,
                "duration": round(duration, 3),
                "timestamp": datetime.utcnow().isoformat(),
            }

            if self.include_payloads and hasattr(response, "result"):
                audit_data["result"] = self._sanitize_data(response.result)

            self.audit_logger.info(json.dumps(audit_data))
            return response

        except Exception as e:
            duration = time.time() - start_time

            # Record error response
            audit_data = {
                "event": "request_error",
                "request_id": request_id,
                "user_id": user_id,
                "method": method,
                "duration": round(duration, 3),
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.audit_logger.info(json.dumps(audit_data))
            raise


class CacheMiddleware:
    """Cache Middleware

    Provides simple in-memory caching for read-only operations
    """

    def __init__(
        self,
        cache_ttl: int = 300,  # 5 minutes
        max_cache_size: int = 1000,
        cacheable_methods: list[str] | None = None,
        **config: Any,
    ) -> None:
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size
        self.cacheable_methods = set(cacheable_methods or ["list_tools", "list_resources", "get_resource"])
        self.cache: dict[str, tuple[Any, float]] = {}  # {cache_key: (response, timestamp)}
        self.config = config
        logger.info(f"CacheMiddleware initialized: ttl={cache_ttl}s, max_size={max_cache_size}")

    def _get_cache_key(self, request: Any) -> str:
        """Generate cache key"""
        method = getattr(request, "method", "")
        params = getattr(request, "params", {})

        # Create deterministic cache key
        key_data = f"{method}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache is still valid"""
        return time.time() - timestamp < self.cache_ttl

    def _cleanup_cache(self) -> None:
        """Clean up expired cache items"""
        current_time = time.time()
        expired_keys = [key for key, (_, timestamp) in self.cache.items() if current_time - timestamp >= self.cache_ttl]

        for key in expired_keys:
            del self.cache[key]

        # If cache is still too large, remove oldest items
        if len(self.cache) > self.max_cache_size:
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1][1])
            items_to_remove = len(self.cache) - self.max_cache_size

            for i in range(items_to_remove):
                key = sorted_items[i][0]
                del self.cache[key]

    async def __call__(self, request: Any, call_next: Any) -> Any:
        """Handle cache logic"""
        method = getattr(request, "method", "")

        # Only cache cacheable methods
        if method not in self.cacheable_methods:
            return await call_next(request)

        cache_key = self._get_cache_key(request)

        # Check cache
        if cache_key in self.cache:
            cached_response, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                logger.debug(f"Cache hit for {method}")
                return cached_response
            else:
                # Remove expired cache item
                del self.cache[cache_key]

        # Execute request
        response = await call_next(request)

        # Cache response
        self.cache[cache_key] = (response, time.time())
        logger.debug(f"Cached response for {method}")

        # Periodically clean up cache
        if len(self.cache) > self.max_cache_size * 1.2:
            self._cleanup_cache()

        return response


# ============================================================================
# Usage Examples
# ============================================================================


def create_enterprise_config() -> dict[str, Any]:
    """Create enterprise-grade configuration example"""
    return {
        "server": {
            "name": "Enterprise MCP Server",
            "instructions": "Enterprise-grade MCP server with authentication, audit, and caching capabilities"
        },
        "middleware": [
            # 1. Authentication middleware (executed first)
            {
                "type": "custom",
                "class": "examples.custom_middleware.AuthenticationMiddleware",
                "config": {
                    "api_keys": ["secret-key-1", "secret-key-2", "secret-key-3"],
                    "header_name": "X-API-Key",
                    "allow_anonymous": False,
                },
                "enabled": True,
            },
            # 2. Audit middleware
            {
                "type": "custom",
                "class": "examples.custom_middleware.AuditMiddleware",
                "config": {
                    "log_file": "mcp_audit.log",
                    "include_payloads": True,
                    "sensitive_fields": ["password", "token", "api_key", "secret"],
                },
                "enabled": True,
            },
            # 3. Cache middleware
            {
                "type": "custom",
                "class": "examples.custom_middleware.CacheMiddleware",
                "config": {
                    "cache_ttl": 600,  # 10 minutes
                    "max_cache_size": 500,
                    "cacheable_methods": ["list_tools", "list_resources"],
                },
                "enabled": True,
            },
            # 4. FastMCP built-in middleware
            {"type": "timing", "config": {"log_level": 20}, "enabled": True},
            {
                "type": "error_handling",
                "config": {"include_traceback": True, "transform_errors": True},
                "enabled": True,
            },
        ],
        "transport": {"type": "stdio"},
    }


if __name__ == "__main__":
    # Test middleware here
    print("🏢 Enterprise-grade Custom Middleware Examples")
    print("📁 Middleware implementation location: examples/custom_middleware.py")
    print("🔧 Includes the following custom middleware:")
    print("   1. AuthenticationMiddleware - API key authentication")
    print("   2. AuditMiddleware - Security audit logging")
    print("   3. CacheMiddleware - Intelligent response caching")
    print()
    print("💡 Users can implement custom middleware anywhere in their project:")
    print("   - my_project/middleware/auth.py")
    print("   - my_project/utils/custom_middleware.py")
    print("   - my_project/security/middleware.py")
    print("   - Any importable Python module")
