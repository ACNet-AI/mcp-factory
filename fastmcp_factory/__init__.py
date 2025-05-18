"""FastMCP Factory package.

Provides factory pattern and extended management server functionality for FastMCP,
simplifying server creation and management.
"""

from .factory import FastMCPFactory
from .server import ManagedServer

__all__ = ["ManagedServer", "FastMCPFactory"]
