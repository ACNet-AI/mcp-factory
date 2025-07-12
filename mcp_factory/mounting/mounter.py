"""
MCP Factory Mounting - Server Mounter

Responsible for mounting, unmounting and runtime management of external MCP servers.
Supports mounting of local script servers (stdio) and remote HTTP servers (streamable-http/sse).
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from collections.abc import Awaitable, Callable
from typing import Any

try:
    import httpx

    httpx_available = True
except ImportError:
    httpx = None  # type: ignore
    httpx_available = False

import contextlib

from fastmcp import Client, FastMCP

from ..exceptions import ErrorHandler, MountingError, ServerError
from .models import MountedServerInfo, ServerConfig

logger = logging.getLogger(__name__)


class ServerMounter:
    """Server Mounter - Responsible for mounting external MCP servers"""

    def __init__(self, main_server: FastMCP[Any], mount_options: dict[str, Any] | None = None):
        self.main_server = main_server
        self.mount_options = mount_options or {}
        self.mounted_servers: dict[str, MountedServerInfo] = {}

        # Default mount options
        self.prefix_tools = self.mount_options.get("prefix_tools", True)
        self.prefix_resources = self.mount_options.get("prefix_resources", True)
        self.auto_start = self.mount_options.get("auto_start", True)
        self.health_check = self.mount_options.get("health_check", True)
        self.health_check_interval = self.mount_options.get("health_check_interval", 30)
        self.auto_restart = self.mount_options.get("auto_restart", False)
        self.max_restart_attempts = self.mount_options.get("max_restart_attempts", 3)
        self.restart_delay = self.mount_options.get("restart_delay", 5)

        # Health check task
        self._health_check_task: asyncio.Task[None] | None = None

        # Error handling
        self.error_handler = ErrorHandler("ServerMounter", logger, enable_metrics=True)

    async def initialize(self) -> None:
        """Initialize mounter"""
        logger.info("Initializing server mounter")

        # Start health check
        if self.health_check:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def mount_server(self, server_name: str, config: ServerConfig) -> bool:
        """Mount specified server"""
        logger.info("Mounting server: %s", server_name)

        try:
            prefix = server_name if self.prefix_tools else ""
            server_info = MountedServerInfo(name=server_name, config=config, prefix=prefix)

            server_info.status = "starting"
            self.mounted_servers[server_name] = server_info

            if server_info.is_local:
                success = await self._start_local_server(server_info)
            elif server_info.is_remote:
                success = await self._start_remote_server(server_info)
            else:
                logger.error("Unsupported server configuration: %s", server_name)
                return False

            if success:
                # Mount to main server
                await self._mount_to_main_server(server_info)
                server_info.status = "running"
                server_info.restart_attempts = 0
                logger.info("Successfully mounted server: %s", server_name)
                return True
            server_info.status = "failed"
            return False

        except (MountingError, ServerError) as e:
            logger.error("Failed to mount server %s: %s", server_name, e)
            if server_name in self.mounted_servers:
                self.mounted_servers[server_name].status = "failed"
                self.mounted_servers[server_name].error_message = str(e)
            return False
        except Exception as e:
            # Handle unexpected errors
            self.error_handler.handle_error(
                "mount_server", e, {"server_name": server_name, "mount_point": server_name}, reraise=False
            )
            if server_name in self.mounted_servers:
                self.mounted_servers[server_name].status = "failed"
                self.mounted_servers[server_name].error_message = str(e)
            return False

    async def _start_local_server(self, server_info: MountedServerInfo) -> bool:
        """Start local script server"""
        config = server_info.config

        try:
            # Start subprocess
            command_list = [config.command] + (config.args or [])
            # Ensure all command arguments are strings
            full_command = [str(arg) for arg in command_list if arg is not None]
            logger.debug("Executing command: %s", " ".join(full_command))

            # Use proper resource management for subprocess
            try:
                process = subprocess.Popen(
                    full_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={**os.environ, **config.env} if config.env else None,
                    text=True,
                )
                server_info.process = process
            except (OSError, subprocess.SubprocessError, Exception) as e:
                # Ensure cleanup if process creation fails
                if "process" in locals() and process is not None:
                    process.terminate()
                logger.error("Failed to create subprocess for %s: %s", server_info.name, e)
                return False

            # Wait for process to start
            await asyncio.sleep(1)

            if process.poll() is not None:
                logger.error("Local server process failed to start: %s", server_info.name)
                return False

            # Create client connection - special handling needed for local stdio servers
            # Note: FastMCP Client is primarily for HTTP connections, stdio connections need different handling
            # Skip client creation for now, as FastMCP primarily supports HTTP transport
            logger.warning(
                f"Local stdio server {server_info.name} started successfully, but FastMCP Client supports HTTP"
            )

            return True

        except (OSError, subprocess.SubprocessError, asyncio.TimeoutError) as e:
            self.error_handler.handle_error(
                "start_local_server",
                e,
                {"server_name": server_info.name, "mount_point": server_info.name},
                reraise=False,
            )
            return False

    async def _start_remote_server(self, server_info: MountedServerInfo) -> bool:
        """Start remote HTTP server connection"""
        config = server_info.config

        # Test connection
        if not httpx_available:
            logger.error("httpx installation required to support remote server connections")
            return False

        try:
            # Create client connection - FastMCP Client created via URL
            server_info.client = Client(config.url)

            # Test connection - using context manager
            async with server_info.client:
                await server_info.client.list_tools()  # Test connection
            return True

        except (ConnectionError, OSError, TimeoutError, Exception) as e:
            self.error_handler.handle_error(
                "start_remote_server",
                e,
                {"server_name": server_info.name, "mount_point": server_info.name},
                reraise=False,
            )
            return False

    async def _test_server_connection(self, server_info: MountedServerInfo) -> None:
        """Test server connection"""
        if server_info.client is None:
            raise MountingError(
                f"Client for server {server_info.name} is not initialized", mount_point=server_info.name
            )

        try:
            # Test connection using context manager
            async with server_info.client:
                await server_info.client.list_tools()
        except (ConnectionError, OSError, TimeoutError) as e:
            raise MountingError(
                f"Server connection test failed: {e}", mount_point=server_info.name, operation="test_server_connection"
            ) from e

    async def _mount_to_main_server(self, server_info: MountedServerInfo) -> None:
        """Mount server to main server"""
        if server_info.client is None:
            raise MountingError(
                f"Client for server {server_info.name} is not initialized", mount_point=server_info.name
            )

        try:
            # Use context manager to get server tools, resources, etc.
            async with server_info.client:
                tools = await server_info.client.list_tools()
                resources = await server_info.client.list_resources()

                # Proxy tools
                for tool in tools:
                    tool_name = f"{server_info.prefix}_{tool.name}" if server_info.prefix else tool.name

                    def create_proxy_tool(tool_name_param: str, client: Any) -> Callable[..., Awaitable[Any]]:
                        async def proxy_tool(*args: Any, **kwargs: Any) -> Any:
                            async with client:
                                return await client.call_tool(tool_name_param, kwargs)

                        return proxy_tool

                    self.main_server.tool(name=tool_name)(create_proxy_tool(tool.name, server_info.client))

                # Proxy resources
                for resource in resources:
                    resource_uri = f"{resource.uri}"
                    if server_info.prefix:
                        # Use path format prefix
                        parts = resource_uri.split("://", 1)
                        if len(parts) == 2:
                            protocol, path = parts
                            resource_uri = f"{protocol}://{server_info.prefix}/{path}"

                    def create_proxy_resource(resource_uri_param: str, client: Any) -> Callable[[str], Awaitable[Any]]:
                        async def proxy_resource(uri: str) -> Any:
                            async with client:
                                return await client.read_resource(resource_uri_param)

                        return proxy_resource

                    self.main_server.resource(uri=resource_uri)(
                        create_proxy_resource(str(resource.uri), server_info.client)
                    )

        except (ConnectionError, OSError, AttributeError) as e:
            raise MountingError(
                f"Failed to mount server to main server: {e}",
                mount_point=server_info.name,
                operation="mount_to_main_server",
            ) from e

    async def unmount_server(self, server_name: str) -> bool:
        """Unmount specified server"""
        if server_name not in self.mounted_servers:
            logger.warning("Server not mounted: %s", server_name)
            return False

        server_info = self.mounted_servers[server_name]
        logger.info("Unmounting server: %s", server_name)

        try:
            # FastMCP Client uses context manager, no need to manually disconnect
            # Client connections will be automatically closed when context manager exits

            # Terminate local process
            if server_info.process:
                try:
                    server_info.process.terminate()
                    try:
                        server_info.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        server_info.process.kill()
                except (OSError, AttributeError, Exception) as e:
                    logger.error("Failed to terminate process: %s", e)
                    # If process termination fails, reraise to trigger outer exception handler
                    raise

            # Remove from mounted list
            del self.mounted_servers[server_name]
            logger.info("Successfully unmounted server: %s", server_name)
            return True

        except (OSError, subprocess.SubprocessError, KeyError, Exception) as e:
            self.error_handler.handle_error(
                "unmount_server", e, {"server_name": server_name, "mount_point": server_name}, reraise=False
            )
            return False

    async def unmount_all_servers(self) -> None:
        """Unmount all servers"""
        logger.info("Unmounting all mounted servers")

        tasks = []
        for server_name in list(self.mounted_servers.keys()):
            tasks.append(self.unmount_server(server_name))

        # Concurrently unmount all servers
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Stop health checks
        if self._health_check_task:
            self._health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_check_task

        success_count = sum(1 for r in results if r is True)
        logger.info("Successfully unmounted %s/%s servers", success_count, len(results))

    async def _health_check_loop(self) -> None:
        """Health check loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except (ConnectionError, OSError, TimeoutError, Exception) as e:
                logger.error("Health check failed: %s", e)

    async def _perform_health_checks(self) -> None:
        """Perform health checks"""
        for server_info in self.mounted_servers.values():
            if server_info.status != "running":
                continue

            try:
                # Simple health check - try to get tools using context manager
                if server_info.client is not None:
                    async with server_info.client:
                        await server_info.client.list_tools()
                    server_info.last_health_check = time.time()

            except (ConnectionError, OSError, TimeoutError, Exception) as e:
                logger.warning("Server health check failed %s: %s", server_info.name, e)
                server_info.status = "failed"
                server_info.error_message = str(e)

                # Auto restart
                if self.auto_restart and server_info.restart_attempts < self.max_restart_attempts:
                    logger.info("Attempting to restart server %s", server_info.name)
                    server_info.restart_attempts += 1
                    await asyncio.sleep(self.restart_delay)

                    # Remount
                    await self.mount_server(server_info.name, server_info.config)

    def get_server_status(self, server_name: str) -> dict[str, Any] | None:
        """Get server status"""
        if server_name not in self.mounted_servers:
            return None

        server_info = self.mounted_servers[server_name]
        return {
            "name": server_info.name,
            "status": server_info.status,
            "transport": server_info.transport,
            "prefix": server_info.prefix,
            "last_health_check": server_info.last_health_check,
            "restart_attempts": server_info.restart_attempts,
            "error_message": server_info.error_message,
            "config": server_info.config,
        }

    def list_mounted_servers(self) -> list[dict[str, Any]]:
        """List all mounted servers"""
        return [
            status for status in [self.get_server_status(name) for name in self.mounted_servers] if status is not None
        ]
