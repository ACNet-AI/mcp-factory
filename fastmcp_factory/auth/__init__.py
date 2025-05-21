"""FastMCP authentication module package.

Provides implementations of various authentication providers to support
FastMCP's authentication mechanism.
"""

from fastmcp_factory.auth.registry import AuthProviderRegistry

__all__ = ["AuthProviderRegistry"]
