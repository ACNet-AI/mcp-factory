"""
MCP Factory Mounting - External Server Mounting Module

Provides external MCP server configuration parsing, mounting and lifecycle management functionality:
- ServerMounter: Server mounter, responsible for mounting/unmounting external MCP servers
- ServerRegistry: Server registry, responsible for configuration parsing and management
- Data models: DiscoveredServer, ServerConfig, MountedServerInfo

Core functionality:
- Parse mcpServers configuration section
- Mount/unmount external MCP servers
- Manage mounted server lifecycle
- Integrate with FastMCP lifespan

Note: Server discovery functionality should be completed by Agent using crawler MCP server
"""

# Import main classes
from .models import DiscoveredServer, MountedServerInfo, ServerConfig
from .mounter import ServerMounter
from .registry import ServerRegistry

__all__ = ["DiscoveredServer", "MountedServerInfo", "ServerConfig", "ServerMounter", "ServerRegistry"]
