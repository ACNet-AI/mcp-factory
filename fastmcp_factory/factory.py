"""FastMCP factory module, providing unified creation and management of ManagedServer instances.

This module contains the FastMCPFactory class for creating and managing ManagedServer instances.
"""

# fastmcp_factory/factory.py

from typing import Any, Dict, List, Optional

from mcp.server.auth.provider import OAuthAuthorizationServerProvider

from .server import ManagedServer


class FastMCPFactory:
    """FastMCPFactory for unified creation and management of ManagedServer instances.

    Supports injection of auth_server_provider and extended global configuration.
    """

    def __init__(
        self,
        auth_server_provider: Optional[OAuthAuthorizationServerProvider[Any, Any, Any]] = None,
        **factory_config: Any,
    ) -> None:
        """Initialize the FastMCPFactory.

        Args:
            auth_server_provider: Authentication service provider (strongly recommended)
            **factory_config: Other global configurations, extensible
        """
        self.auth_server_provider = auth_server_provider
        self.factory_config = factory_config or {}
        self.servers: Dict[str, ManagedServer] = {}

    def create_managed_server(
        self, name: Optional[str] = None, auto_register: bool = True, **server_kwargs: Any
    ) -> ManagedServer:
        """Create a ManagedServer and automatically inject authentication and global configuration.

        Args:
            name: Server name
            auto_register: Whether to automatically register management tools
            **server_kwargs: Other parameters passed to ManagedServer

        Returns:
            ManagedServer instance
        """
        if name is None and "name" in server_kwargs:
            name = server_kwargs.pop("name")

        # Use provided parameters first, otherwise use factory's
        if "auth_server_provider" not in server_kwargs and self.auth_server_provider:
            server_kwargs["auth_server_provider"] = self.auth_server_provider

        server = ManagedServer(
            name=name, auto_register=auto_register, **{**self.factory_config, **server_kwargs}
        )

        if name:
            self.servers[name] = server

        return server

    def get_server(self, name: str) -> Optional[ManagedServer]:
        """Get a server by name.

        Args:
            name: Server name

        Returns:
            ManagedServer instance or None
        """
        return self.servers.get(name)

    def list_servers(self) -> List[str]:
        """Get a list of all server names.

        Returns:
            List of server names
        """
        return list(self.servers.keys())

    def remove_server(self, name: str) -> bool:
        """Remove a server by name.

        Args:
            name: Server name

        Returns:
            True if the server was found and removed, False otherwise
        """
        if name in self.servers:
            del self.servers[name]
            return True
        return False
