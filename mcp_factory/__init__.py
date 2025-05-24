"""FastMCP Factory - A server factory for automatic tool registration.

Provides remote invocation, and permission management capabilities.
"""

__version__ = "0.2.0"

# Export main classes
# Export parameter utility module for custom server configuration
from mcp_factory import param_utils
from mcp_factory.auth import AuthProviderRegistry
from mcp_factory.factory import FastMCPFactory
from mcp_factory.server import ManagedServer

__all__ = [
    "FastMCPFactory",
    "ManagedServer",
    "AuthProviderRegistry",
    "param_utils",
]
