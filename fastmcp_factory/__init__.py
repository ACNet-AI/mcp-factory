"""FastMCP Factory - A server factory for automatic tool registration.

Provides remote invocation, and permission management capabilities.
"""

__version__ = "0.1.0"

# Export main classes
# Export parameter utility module for custom server configuration
from fastmcp_factory import param_utils
from fastmcp_factory.auth import AuthProviderRegistry
from fastmcp_factory.factory import FastMCPFactory
from fastmcp_factory.server import ManagedServer

__all__ = [
    "FastMCPFactory",
    "ManagedServer",
    "AuthProviderRegistry",
    "param_utils",
]
