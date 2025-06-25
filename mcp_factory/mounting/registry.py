"""
MCP Factory Mounting - Registry and Configuration Management

Responsible for external server configuration parsing, registry management and lifespan integration.
Focuses on parsing mcpServers configuration sections and server configuration management.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

from .models import DiscoveredServer, ServerConfig
from .mounter import ServerMounter

logger = logging.getLogger(__name__)


class ServerRegistry:
    """Server Registry - responsible for configuration management and lifespan integration"""

    def __init__(self, main_server: FastMCP):
        self.main_server = main_server
        self.server_configs: dict[str, ServerConfig] = {}
        self.mounter: ServerMounter | None = None

    def parse_external_servers_config(self, config: dict[str, Any]) -> dict[str, ServerConfig]:
        """Parse mcpServers configuration"""
        parsed_configs = {}

        external_servers = config.get("mcpServers", {})
        for server_name, server_config in external_servers.items():
            try:
                parsed_config = self._parse_single_server_config(server_name, server_config)
                parsed_configs[server_name] = parsed_config
                logger.debug(f"Parsing server configuration: {server_name}")
            except Exception as e:
                logger.error(f"Failed to parse server configuration {server_name}: {e}")

        logger.info(f"Successfully parsed {len(parsed_configs)} server configurations")
        return parsed_configs

    def _parse_single_server_config(self, name: str, config: dict[str, Any]) -> ServerConfig:
        """Parse single server configuration"""
        return ServerConfig(
            name=name,
            command=config.get("command"),
            args=config.get("args", []),
            env=config.get("env", {}),
            url=config.get("url"),
            transport=config.get("transport"),
            headers=config.get("headers", {}),
            timeout=config.get("timeout", 30.0),
        )

    def register_servers(self, configs: dict[str, ServerConfig]) -> None:
        """Register server configurations"""
        self.server_configs.update(configs)
        logger.info(f"Registered {len(configs)} server configurations")

    def register_discovered_server(
        self, discovered: DiscoveredServer, custom_config: dict[str, Any] | None = None
    ) -> ServerConfig:
        """Register discovered server with optional custom configuration"""
        # Use discovered server template as base
        base_config = discovered.config_template.copy()

        # Apply custom configuration
        if custom_config:
            base_config.update(custom_config)

        # Create ServerConfig object
        server_config = self._parse_single_server_config(discovered.name, base_config)

        # Register to configuration
        self.server_configs[discovered.name] = server_config

        logger.info(f"Registered discovered server: {discovered.name}")
        return server_config

    def get_server_config(self, name: str) -> ServerConfig | None:
        """Get server configuration"""
        return self.server_configs.get(name)

    def list_registered_servers(self) -> list[str]:
        """List registered server names"""
        return list(self.server_configs.keys())

    def create_lifespan(self, mount_options: dict[str, Any] | None = None) -> Any:
        """Create lifespan function for FastMCP integration"""

        async def lifespan() -> Any:
            """Server lifecycle management"""
            logger.info("Starting server mounting lifecycle")

            # Create mounter
            self.mounter = ServerMounter(self.main_server, mount_options)
            await self.mounter.initialize()

            # Auto-mount configured servers
            if mount_options and mount_options.get("auto_start", True):
                await self._auto_mount_servers()

            try:
                yield  # During server runtime
            finally:
                # Clean up resources
                logger.info("Stopping server mounting lifecycle")
                if self.mounter:
                    await self.mounter.unmount_all_servers()

        return lifespan

    async def _auto_mount_servers(self) -> None:
        """Auto-mount registered servers"""
        if not self.mounter:
            logger.warning("Mounter not initialized, skipping auto-mount")
            return

        mount_tasks = []
        for server_name, server_config in self.server_configs.items():
            logger.info(f"Auto-mounting server: {server_name}")
            # Create coroutine task instead of immediate execution
            task = self.mounter.mount_server(server_name, server_config)
            mount_tasks.append(task)

        # Concurrently mount all servers
        if mount_tasks:
            results = await asyncio.gather(*mount_tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            logger.info(f"Auto-mount completed: {success_count}/{len(results)} servers successful")

    def get_mounter(self) -> ServerMounter | None:
        """Get mounter instance"""
        return self.mounter

    def update_server_config(self, name: str, config_updates: dict[str, Any]) -> None:
        """Update server configuration"""
        if name not in self.server_configs:
            logger.warning(f"Server configuration does not exist: {name}")
            return

        current_config = self.server_configs[name]

        # Update configuration fields
        for key, value in config_updates.items():
            if hasattr(current_config, key):
                setattr(current_config, key, value)
            else:
                logger.warning(f"Unknown configuration field: {key}")

        logger.info(f"Updated server configuration: {name}")

    def remove_server_config(self, name: str) -> None:
        """Remove server configuration"""
        if name in self.server_configs:
            del self.server_configs[name]
            logger.info(f"Removed server configuration: {name}")
        else:
            logger.warning(f"Server configuration does not exist: {name}")

    def validate_configs(self) -> dict[str, Any]:
        """Validate all server configurations"""
        validation_results = {}

        for name, config in self.server_configs.items():
            result = self._validate_single_config(config)
            validation_results[name] = result

        return validation_results

    def _validate_single_config(self, config: ServerConfig) -> dict[str, Any]:
        """Validate single server configuration"""
        result: dict[str, Any] = {"valid": True, "errors": [], "warnings": []}

        # Check local server configuration
        if config.is_local and not config.command:
            result["valid"] = False
            result["errors"].append("Local server must specify command")

        # Check remote server configuration
        if config.is_remote and not config.url:
            result["valid"] = False
            result["errors"].append("Remote server must specify url")
        elif config.is_remote and config.url and not config.url.startswith(("http://", "https://")):
            result["warnings"].append("URL should start with http:// or https://")

        # Check basic configuration (neither local nor remote)
        if not config.is_local and not config.is_remote:
            result["valid"] = False
            result["errors"].append("Must specify command or url")

        return result
