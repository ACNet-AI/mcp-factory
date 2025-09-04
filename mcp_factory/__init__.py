"""MCP Factory - FastMCP Factory Module.

Provides simplified MCP server creation and management functionality
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__version__ = "1.4.0"

# Import adapters module, but don't expose directly in __all__,
# users access via mcp_factory.adapters.xxx
from . import adapters
from .factory import MCPFactory
from .server import ManagedServer

__all__ = [
    # Core classes
    "MCPFactory",
    "ManagedServer",
    # Adapters module
    "adapters",
    # Version
    "__version__",
]

# ============================================================================
# Convenience functions
# ============================================================================


def create_factory(workspace_root: str = "./workspace") -> MCPFactory:
    """Create MCP factory instance

    Args:
        workspace_root: Workspace root directory

    Returns:
        MCPFactory: Factory instance
    """
    return MCPFactory(workspace_root=workspace_root)


def create_server(
    name: str,
    config_source: str | dict[str, Any] | Path,
    workspace: str | None = None,
    **kwargs: Any,
) -> tuple[MCPFactory, str | None]:
    """Quickly create server

    Args:
        name: Server name
        config_source: Configuration dictionary or project path
        workspace: Workspace
        **kwargs: Other server parameters

    Returns:
        tuple[MCPFactory, str | None]: (Factory instance, Server ID)
    """
    factory = MCPFactory(workspace_root=workspace or "./workspace")
    # Ensure config_source is not None
    actual_config_source = config_source if config_source is not None else {}
    server_id: str | None = factory.create_server(name, actual_config_source, **kwargs)
    return factory, server_id
