"""MCP Factory - Factory class for creating and managing MCP servers

This module provides the MCPFactory class for:
1. Creating and managing MCP server instances
2. Creating servers from configuration files or dictionaries
3. Managing server lifecycle
4. Providing server state management
"""

from __future__ import annotations

import contextlib
import json
import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .config import get_default_config, normalize_config, validate_config
from .exceptions import ErrorHandler, ProjectError, ServerError, ValidationError
from .project import Builder
from .project.components import ComponentManager
from .server import ManagedServer

logger = logging.getLogger(__name__)


# ============================================================================
# Helper utility classes
# ============================================================================


class ServerStateManager:
    """Balanced State Manager - Retain useful fields while simplifying data structure

    Core principles:
    - Retain fields needed by CLI and functionality (status, last_updated, event)
    - Auto-convert dict_config to config_file
    - Simplify but don't over-delete useful information
    """

    VALID_STATUSES = {"created", "starting", "running", "stopping", "stopped", "error", "restarting"}

    def __init__(self, workspace_root: Path) -> None:
        """Initialize state manager"""
        self.workspace_root = Path(workspace_root)
        self.state_file = self.workspace_root / ".servers_state.json"
        self._servers: dict[str, dict[str, Any]] = {}
        self._load_servers()

    def initialize_server_state(self, server_id: str, server_name: str, config: dict[str, Any]) -> None:
        """Initialize server state"""
        import time

        import yaml

        current_time = time.time()
        source_type = config.get("source_type", "unknown")
        source_path = config.get("source_path")

        # 🔄 Force conversion: Auto-convert all dict_config to config_file
        if source_type == "dict_config":
            configs_dir = self.workspace_root / "configs"
            configs_dir.mkdir(exist_ok=True)

            # Generate config file name
            safe_name = "".join(c for c in server_name if c.isalnum() or c in ("-", "_")).rstrip()
            config_filename = f"{safe_name}-{server_id[:8]}.yaml"
            config_path = configs_dir / config_filename

            # Clean config and save
            cleaned_config = self._clean_config_for_storage(config)
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(cleaned_config, f, default_flow_style=False, allow_unicode=True)

            # Update to config_file type
            source_type = "config_file"
            source_path = str(config_path.relative_to(self.workspace_root))

            logger.info("Auto-converted dict_config to config_file: %s", source_path)

        # 🎯 Balanced state format - Retain useful fields
        self._servers[server_id] = {
            "name": server_name,
            "status": "created",
            "created_at": current_time,
            "last_updated": current_time,
            "source_type": source_type,
            "source_path": source_path,
            "last_event": "created",
        }

        self._save_servers()

    def update_server_state(self, server_id: str, status: str | None = None, **updates: Any) -> None:
        """Update server state"""
        if server_id not in self._servers:
            logger.warning("Server %s not found, skipping update", server_id)
            return

        # Validate status
        if status and status not in self.VALID_STATUSES:
            logger.warning("Invalid status '%s' for server %s, using 'error'", status, server_id)
            status = "error"

        # Update status
        if status:
            self._servers[server_id]["status"] = status
        self._servers[server_id]["last_updated"] = __import__("time").time()

        # Update other fields
        for key, value in updates.items():
            if key not in ["created_at", "source_type", "source_path"]:  # Protect important fields
                self._servers[server_id][key] = value

        self._save_servers()

    def get_server_state(self, server_id: str) -> dict[str, Any]:
        """Get server state"""
        return self._servers.get(server_id, {})

    def get_servers_summary(self) -> dict[str, dict[str, Any]]:
        """Get all servers summary"""
        return self._servers.copy()

    def remove_server_state(self, server_id: str) -> None:
        """Remove server state and cleanup auto-generated config files"""
        if server_id in self._servers:
            server_state = self._servers[server_id]

            # Cleanup auto-generated config files
            self._cleanup_auto_generated_config(server_id, server_state)

            # Remove state record
            del self._servers[server_id]
            self._save_servers()

    def record_server_event(self, server_id: str, event: str, details: dict[str, Any] | None = None) -> None:
        """Record server event"""
        if server_id in self._servers:
            self._servers[server_id]["last_event"] = event
            self._servers[server_id]["last_updated"] = __import__("time").time()
            if details:
                self._servers[server_id]["last_event_details"] = details
            self._save_servers()

    def get_server_config(self, server_id: str) -> dict[str, Any] | None:
        """Get server configuration"""
        server_state = self._servers.get(server_id)
        if not server_state:
            return None

        source_path = server_state.get("source_path")
        if source_path:
            try:
                return self._load_config_from_source(source_path)
            except Exception as e:
                logger.error("Failed to load config from %s: %s", source_path, e)
        return None

    def _load_servers(self) -> None:
        """Load server state from file"""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, encoding="utf-8") as f:
                self._servers = json.load(f)
            logger.debug("Loaded %s servers from state file", len(self._servers))
        except Exception as e:
            logger.error("Failed to load servers state: %s", e)
            self._servers = {}

    def _save_servers(self) -> None:
        """Save server state to file"""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self._servers, f, indent=2, ensure_ascii=False, default=str)
            logger.debug("Saved %s servers to state file", len(self._servers))
        except Exception as e:
            logger.error("Failed to save servers state: %s", e)

    def _cleanup_auto_generated_config(self, server_id: str, server_state: dict[str, Any]) -> None:
        """Cleanup auto-generated config files"""
        source_type = server_state.get("source_type")
        source_path = server_state.get("source_path")

        # Only cleanup auto-generated config_file type files
        if source_type != "config_file" or not source_path:
            return

        # Check if it's an auto-generated config file
        if not self._is_auto_generated_config(server_id, source_path):
            logger.info("Preserving user-created config file: %s", source_path)
            return

        # Delete auto-generated config file
        try:
            config_file_path = self.workspace_root / source_path
            if config_file_path.exists():
                config_file_path.unlink()
                logger.info("Cleaned up auto-generated config file: %s", source_path)
        except Exception as e:
            logger.warning("Failed to cleanup config file %s: %s", source_path, e)

    def _is_auto_generated_config(self, server_id: str, source_path: str) -> bool:
        """Check if it's an auto-generated config file"""
        if not source_path:
            return False

        # Auto-generated config file feature: contains first 8 characters of server_id
        return server_id[:8] in source_path

    def _clean_config_for_storage(self, config: dict[str, Any]) -> dict[str, Any]:
        """Clean config for storage"""
        cleaned_config = config.copy()

        # Remove metadata fields
        cleaned_config.pop("source_type", None)
        cleaned_config.pop("source_path", None)

        return cleaned_config

    def _load_config_from_source(self, source_path: str) -> dict[str, Any]:
        """Load config from source path"""
        source_path_obj = Path(source_path)

        # If path is relative, resolve it relative to workspace_root
        if not source_path_obj.is_absolute():
            source_path_obj = self.workspace_root / source_path_obj

        if not source_path_obj.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")

        if source_path_obj.is_file():
            # Config file
            with open(source_path_obj, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        elif source_path_obj.is_dir():
            # Project directory
            config_file = source_path_obj / "config.yaml"
            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            else:
                from .config import get_default_config

                return get_default_config()
        else:
            raise ValueError(f"Invalid source path: {source_path}")

    # Compatibility methods
    def get_server_details(self, server_id: str) -> dict[str, Any]:
        """Get server details (compatibility method)"""
        return self.get_server_state(server_id)

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """Get all states (compatibility method)"""
        return self.get_servers_summary()

    def update_server_status(self, server_id: str, status: str) -> None:
        """Update server status (compatibility method)"""
        self.update_server_state(server_id, status=status)


# ============================================================================
# MCP Factory Main Class
# ============================================================================


class MCPFactory:
    """MCP Server Factory - Complete Version"""

    def __init__(self, workspace_root: str = "./workspace") -> None:
        """Initialize factory

        Args:
            workspace_root: Workspace root directory
        """
        try:
            self.workspace_root = Path(workspace_root)

            # Prevent .states directory creation in project root
            # Only redirect if current directory is not already workspace and we're using "."
            current_dir = Path.cwd()
            if workspace_root == "." and not current_dir.name.endswith("workspace"):
                logger.warning(
                    f"Correcting workspace_root from '{workspace_root}' to './workspace' "
                    f"to prevent .states directory creation in project root"
                )
                self.workspace_root = Path("./workspace")
            elif workspace_root == "./workspace" and current_dir.name.endswith("workspace"):
                # If we're already in a workspace directory, use current directory
                logger.debug("Already in workspace directory, using current directory")
                self.workspace_root = Path()

            self.workspace_root.mkdir(parents=True, exist_ok=True)
            self.builder = Builder(str(self.workspace_root))
            self._servers: dict[str, ManagedServer] = {}

            # Initialize components
            self._error_handler = ErrorHandler("mcp_factory")
            self._state_manager = ServerStateManager(self.workspace_root)

            # Restore previous server state
            self._load_servers_state()

            logger.info("MCP Factory initialization completed: %s", self.workspace_root)

        except Exception as e:
            logger.error("Factory initialization failed: %s", e)
            raise

    # =========================================================================
    # Server Management - Core API
    # =========================================================================

    def create_server(
        self,
        name: str,
        source: str | dict[str, Any] | Path,
        auth: dict[str, Any] | Any | None = None,
        lifespan: Callable[[Any], Any] | None = None,
        tool_serializer: Callable[[Any], str] | None = None,
        tools: list[Any] | None = None,
        middleware: list[Any] | None = None,
        expose_management_tools: bool = True,
        **server_kwargs: Any,
    ) -> str | None:
        """Create and manage MCP server

        Args:
            name: Server name
            source: Configuration source (file path, dictionary or project path)
            auth: Authentication configuration
            lifespan: Lifecycle function
            tool_serializer: Tool serializer
            tools: Tool list
            middleware: Middleware list (FastMCP middleware instances)
            expose_management_tools: Whether to expose management tools
            **server_kwargs: Other server parameters

        Returns:
            str | None: Server ID or None
        """
        try:
            # Determine source type before loading config
            source_type, source_path = self._determine_source_type(source)

            config = self._load_config_from_source(source)
            self._apply_all_params(config, name, expose_management_tools, server_kwargs)
            config = self._validate_config(config)  # Use normalized configuration
            server = self._build_server(config, auth, lifespan, tool_serializer, tools, middleware)
            self._add_components(server, source)
            server_id = self._register_server(server, name)
            # Extract config for state initialization
            server_config = self._extract_current_server_config(server, server_id)

            # Add source type information to config
            server_config["source_type"] = source_type
            server_config["source_path"] = source_path

            self._state_manager.initialize_server_state(server_id, name, server_config)

            return server_id
        except Exception as e:
            self._error_handler.handle_error("Server creation failed", e, {"server_name": name})
            return None  # Return None instead of re-raising exception

    def get_server(self, server_id: str) -> ManagedServer:
        """Get server instance"""
        if server_id not in self._servers:
            raise ServerError(f"Server does not exist: {server_id}", server_id=server_id)
        return self._servers[server_id]

    def list_servers(self) -> list[dict[str, Any]]:
        """List all servers"""
        return [
            {
                "id": server_id,
                "name": server.name,
                "instructions": (server.instructions[:100] + "...")
                if server.instructions and len(server.instructions) > 100
                else (server.instructions or ""),
                "status": self._state_manager.get_server_state(server_id).get("status", "unknown"),
                "host": getattr(server, "host", "localhost"),
                "port": getattr(server, "port", 8000),
                "project_path": self._get_server_project_path(server_id),
                "created_at": self._state_manager.get_server_state(server_id).get("created_at"),
                "source_type": self._state_manager.get_servers_summary()
                .get(server_id, {})
                .get("source_type", "unknown"),
                "source_path": self._state_manager.get_servers_summary().get(server_id, {}).get("source_path"),
            }
            for server_id, server in self._servers.items()
        ]

    def get_server_status(self, server_id: str) -> dict[str, Any]:
        """Get detailed server status"""
        server = self.get_server(server_id)
        state = self._state_manager.get_server_state(server_id)
        summary = self._state_manager.get_servers_summary().get(server_id, {})

        return {
            "id": server_id,
            "name": server.name,
            "instructions": server.instructions,
            "project_path": self._get_server_project_path(server_id),
            "config": getattr(server, "_config", {}),
            "state": state,
            "expose_management_tools": getattr(server, "expose_management_tools", True),
            "source_type": summary.get("source_type", "unknown"),
            "source_path": summary.get("source_path"),
        }

    def delete_server(self, server_id: str) -> bool:
        """Delete server"""
        try:
            if server_id in self._servers:
                server_name = self._servers[server_id].name
                del self._servers[server_id]
                self._state_manager.remove_server_state(server_id)
                logger.info("Server deleted successfully: %s", server_name)
                return True
            return False
        except Exception as e:
            self._error_handler.handle_error("Failed to delete server", e, {"server_id": server_id})
            return False

    # =========================================================================
    # Server Management - Operations API
    # =========================================================================

    def update_server(self, server_id: str, **params: Any) -> ManagedServer:
        """Update server parameters"""
        try:
            server = self.get_server(server_id)

            updated_count = 0
            for key, value in params.items():
                if hasattr(server, key):
                    setattr(server, key, value)
                    updated_count += 1
                    logger.debug("Updated %s for server %s", key, server_id)

            self._complete_operation(
                server_id,
                "last_updated",
                f"Server configuration update completed: {server.name}, updated {updated_count} parameters",
            )

            return server
        except Exception as e:
            self._error_handler.handle_error("Failed to update server", e, {"server_id": server_id})
            raise  # Re-raise exception to maintain type consistency

    def reload_server_config(self, server_id: str) -> ManagedServer:
        """Reload server configuration"""
        try:
            server = self.get_server(server_id)

            project_path = self._get_server_project_path(server_id)
            if not project_path:
                raise ServerError(f"Server {server_id} has no associated project path", server_id=server_id)

            # Reload configuration
            config_file = Path(project_path) / "config.yaml"
            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    new_config = yaml.safe_load(f)

                if new_config:
                    # Validate and normalize new configuration
                    new_config = self._validate_config(new_config)

                    # Update server configuration
                    server._config = new_config

                    # Re-register components
                    ComponentManager.register_components(server, Path(project_path))

                    self._complete_operation(
                        server_id, "config_reloaded", f"Configuration reload completed: {server.name}"
                    )

            return server
        except Exception as e:
            self._error_handler.handle_error("Failed to reload configuration", e, {"server_id": server_id})
            raise  # Re-raise exception to maintain type consistency

    def restart_server(self, server_id: str) -> ManagedServer:
        """Restart server"""
        try:
            server = self.get_server(server_id)

            # Update state to indicate restart
            self._state_manager.update_server_state(server_id, status="restarting")
            self._state_manager.record_server_event(server_id, "restart_initiated", {"restart_reason": "manual"})

            # If there's a project path, re-register components
            project_path = self._get_server_project_path(server_id)
            if project_path and Path(project_path).exists():
                ComponentManager.register_components(server, Path(project_path))

            self._complete_operation(server_id, "restarted", f"Server restart completed: {server.name}")

            return server
        except Exception as e:
            self._error_handler.handle_error("Failed to restart server", e, {"server_id": server_id})
            raise  # Re-raise exception to maintain type consistency

    def run_server(
        self,
        source: str | dict[str, Any] | Path,
        name: str | None = None,
        transport: str | None = None,
        host: str | None = None,
        port: int | None = None,
        **server_kwargs: Any,
    ) -> str:
        """Run server directly from configuration source

        Args:
            source: Configuration source (file path, dict, or directory)
            name: Server name override (CLI parameter takes priority)
            transport: Transport protocol override
            host: Host address override
            port: Port number override
            **server_kwargs: Additional server parameters

        Returns:
            Server ID of the running server
        """
        try:
            # Load configuration
            config_data = self._load_config_from_source(source)
            server_config = config_data.get("server", {})
            transport_config = config_data.get("transport", {})

            # CLI parameter > config file > default value
            actual_name = name or server_config.get("name") or "runtime-server"

            # Create server
            server_id = self.create_server(actual_name, source, **server_kwargs)
            if server_id is None:
                raise ServerError("Failed to create server")

            # Get server instance
            managed_server = self.get_server(server_id)

            # Determine transport settings with override priority
            # Note: We expect transport settings in transport section per schema
            final_transport = transport or transport_config.get("transport", "stdio")
            final_host = host or transport_config.get("host", "127.0.0.1")
            final_port = port or transport_config.get("port", 8000)

            # Validate transport
            valid_transports = ["stdio", "http", "sse", "streamable-http"]
            if final_transport not in valid_transports:
                final_transport = "stdio"

            # Type cast to satisfy mypy
            from typing import Literal, cast

            transport_typed = cast(Literal["stdio", "http", "sse", "streamable-http"], final_transport)

            # Run server with appropriate parameters
            if transport_typed in ["http", "sse", "streamable-http"]:
                managed_server.run(transport=transport_typed, host=final_host, port=final_port)
            else:
                managed_server.run(transport=transport_typed)

            return server_id

        except Exception as e:
            self._error_handler.handle_error("Failed to run server", e, {"source": str(source)})
            raise  # Re-raise exception to maintain type consistency

    # =========================================================================
    # Project Management
    # =========================================================================

    def build_project(
        self, project_name: str, config_dict: dict[str, Any] | None = None, force: bool = False, git_init: bool = True
    ) -> str:
        """Build new project"""
        try:
            return self.builder.build_project(project_name, config_dict, force, git_init)
        except Exception as e:
            self._error_handler.handle_error("Failed to build project", e, {"project_name": project_name})
            raise  # Re-raise exception to maintain type consistency

    def create_project_and_server(
        self,
        project_name: str,
        config_dict: dict[str, Any],
        force: bool = False,
        **server_kwargs: Any,
    ) -> tuple[str, str | None]:
        """Create project and server instance simultaneously

        Args:
            project_name: Project name
            config_dict: Project configuration dictionary
            force: Whether to force overwrite existing project
            **server_kwargs: Additional parameters passed to server

        Returns:
            tuple: (project_path, server_id)
        """
        try:
            # 1. Build project
            project_path = self.build_project(project_name, config_dict, force)

            # 2. Create server (using project path as configuration source)
            server_id = self.create_server(name=project_name, source=project_path, **server_kwargs)

            return project_path, server_id

        except Exception as e:
            self._error_handler.handle_error("Failed to create project and server", e, {"project_name": project_name})
            raise  # Re-raise exception to maintain type consistency

    def sync_to_project(self, server_id: str, target_path: str | None = None) -> bool:
        """Synchronize server state to project files

        Args:
            server_id: Server ID
            target_path: Target project path, if None use server's associated project path

        Returns:
            bool: Whether synchronization was successful
        """
        try:
            server = self.get_server(server_id)

            # Determine target path
            target_path = target_path or self._get_server_project_path(server_id)
            if not target_path:
                logger.warning("Server %s has no associated project path, cannot synchronize", server_id)
                return False

            project_path = Path(target_path)
            if not project_path.exists():
                logger.error("Target project path does not exist: %s", target_path)
                return False

            # 1. Extract current server configuration state
            current_config = self._extract_current_server_config(server, server_id)

            # 2. Delegate Builder to update configuration file
            self.builder.update_config_file(str(project_path), current_config)

            # 3. Delegate Builder to regenerate server.py (ensure consistency with current configuration)
            self.builder.update_server_file(str(project_path))

            # 4. Update synchronization status
            sync_info = {"timestamp": datetime.now().isoformat(), "target_path": str(project_path)}
            self._state_manager.record_server_event(server_id, "sync_completed", sync_info)
            self._complete_operation(
                server_id, "sync_completed", f"Server state synchronization completed: {server.name} -> {target_path}"
            )
            return True

        except Exception as e:
            logger.error("Failed to synchronize server to project %s: %s", server_id, e)
            return False

    # =========================================================================
    # Internal Methods - Configuration and Building
    # =========================================================================

    def _get_server_project_path(self, server_id: str) -> str | None:
        """Get project path from server source information

        Args:
            server_id: Server ID

        Returns:
            str | None: Project path if server is from project directory, None otherwise
        """
        summary = self._state_manager.get_servers_summary().get(server_id, {})
        source_path = summary.get("source_path")
        if source_path and isinstance(source_path, str) and Path(source_path).is_dir():
            return str(source_path)
        return None

    def _determine_source_type(self, source: str | dict[str, Any] | Path) -> tuple[str, str | None]:
        """Determine the type and path of the server source

        Args:
            source: Configuration source

        Returns:
            tuple[str, str | None]: (source_type, source_path)

        Source types:
        - "dict_config": Dictionary configuration
        - "config_file": Configuration file (.yaml/.yml)
        - "project_dir": Project directory
        """
        try:
            if isinstance(source, dict):
                return ("dict_config", None)

            source_path = Path(source)

            if not source_path.exists():
                # For consistency, treat non-existent paths as potential config files
                return ("config_file", str(source_path))

            if source_path.is_file():
                return ("config_file", str(source_path))
            if source_path.is_dir():
                return ("project_dir", str(source_path))
            # Fallback for special file types
            return ("config_file", str(source_path))

        except Exception as e:
            logger.warning("Failed to determine source type for %s: %s", source, e)
            return ("unknown", str(source) if not isinstance(source, dict) else None)

    def _load_config_from_source(self, source: str | dict[str, Any] | Path) -> dict[str, Any]:
        """Load configuration from various sources"""
        try:
            if isinstance(source, dict):
                return source

            source_path = Path(source)
            if not source_path.exists():
                raise ProjectError(f"Source path does not exist: {source_path}", project_path=str(source_path))

            if source_path.is_file():
                # Individual configuration file
                with open(source_path, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}

            elif source_path.is_dir():
                # Project directory
                config_file = source_path / "config.yaml"
                if config_file.exists():
                    with open(config_file, encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                else:
                    # No configuration file, use default configuration
                    return get_default_config()
            else:
                # This should not happen as we already checked above
                raise ProjectError(f"Invalid source path: {source_path}", project_path=str(source_path))

        except Exception as e:
            self._error_handler.handle_error("Failed to load configuration", e, {"source": str(source)})
            raise  # Re-raise exception to maintain type consistency

    def _apply_all_params(
        self,
        config: dict[str, Any],
        name: str,
        expose_management_tools: bool,
        server_kwargs: dict[str, Any],
    ) -> None:
        """Unified parameter processing: core parameters + runtime overrides"""
        if "server" not in config:
            config["server"] = {}

        config["server"]["name"] = name
        config["server"]["expose_management_tools"] = expose_management_tools

        for key, value in server_kwargs.items():
            if key in ["host", "port", "debug", "transport", "instructions"]:
                config["server"][key] = value
            elif key.startswith("streamable_"):
                if "advanced" not in config:
                    config["advanced"] = {}
                config["advanced"][key] = value
            else:
                config["server"][key] = value

    def _validate_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize configuration

        Returns:
            Normalized configuration dictionary
        """
        try:
            # First normalize configuration, fix common format issues
            normalized_config = normalize_config(config)

            # Then validate normalized configuration
            is_valid, errors = validate_config(normalized_config)
            if not is_valid:
                raise ValidationError(f"Configuration validation failed: {errors}", validation_errors=errors)

            return normalized_config
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Configuration validation error: %s", e)
            raise ValidationError(f"Configuration validation error: {e}") from e

    def _build_server(
        self,
        config: dict[str, Any],
        auth: dict[str, Any] | Any | None,
        lifespan: Callable[[Any], Any] | None,
        tool_serializer: Callable[[Any], str] | None,
        tools: list[Any] | None,
        middleware: list[Any] | None = None,
    ) -> ManagedServer:
        """Build server instance"""
        try:
            server_config = config.get("server", {})
            server_params = {
                "name": server_config.get("name"),
                "instructions": server_config.get("instructions", ""),
                "expose_management_tools": server_config.get("expose_management_tools", True),
            }

            # Handle mounted server lifespan (if there are mounted servers in config and user didn't provide lifespan)
            final_lifespan = self._prepare_lifespan(config, lifespan)

            # Prepare middleware from configuration
            config_middleware = self._prepare_middleware(config)

            # Combine configuration middleware with parameter middleware
            final_middleware = []
            if config_middleware:
                final_middleware.extend(config_middleware)
            if middleware:
                final_middleware.extend(middleware)

            for param_name, param_value in [
                ("auth", auth),
                ("lifespan", final_lifespan),
                ("tool_serializer", tool_serializer),
                ("tools", tools),
                ("middleware", final_middleware if final_middleware else None),
            ]:
                if param_value is not None:
                    server_params[param_name] = param_value

            server = ManagedServer(**server_params)
            server._config = config
            return server
        except Exception as e:
            self._error_handler.handle_error(
                "Failed to build server instance",
                e,
                {"server_name": str(config.get("server", {}).get("name", "unknown"))},
            )
            raise  # Re-raise exception to maintain type consistency

    def _register_server(self, server: ManagedServer, name: str) -> str:
        """Register server to factory management (with deduplication)"""
        # Check if server with same name already exists in state
        existing_server_id = self._find_existing_server_by_name(name)

        if existing_server_id:
            # Reuse existing server ID to avoid duplicates
            logger.info("Reusing existing server ID for: %s", name)
            server_id = existing_server_id
        else:
            # Generate new UUID only if no existing server found
            server_id = str(uuid.uuid4())
            logger.info("Generated new server ID for: %s", name)

        server._server_id = server_id
        server._created_at = datetime.now().isoformat()
        self._servers[server_id] = server
        logger.info("Server registered successfully: %s", name)
        return server_id

    def _find_existing_server_by_name(self, name: str) -> str | None:
        """Find existing server ID by name from state manager"""
        if hasattr(self, "_state_manager") and self._state_manager:
            # Access the internal servers dict from state manager
            for server_id, server_info in self._state_manager._servers.items():
                if server_info.get("name") == name:
                    logger.debug("Found existing server: %s with ID: %s", name, server_id)
                    return server_id
        return None

    def _prepare_lifespan(
        self, config: dict[str, Any], user_lifespan: Callable[[Any], Any] | None
    ) -> Callable[[Any], Any] | None:
        """Prepare lifespan function, integrating external server functionality

        Args:
            config: Server configuration
            user_lifespan: User-provided lifespan function

        Returns:
            Final lifespan function
        """
        # Directly check and create external server lifespan
        mount_lifespan = None
        has_external_servers = bool(config.get("mcpServers"))

        if has_external_servers:
            from mcp_factory.mounting import ServerRegistry

            async def mount_lifespan(server: Any) -> Any:
                """External server lifecycle management"""
                registry = ServerRegistry(server)
                parsed_configs = registry.parse_external_servers_config(config)
                registry.register_servers(parsed_configs)

                lifespan_func = registry.create_lifespan({"auto_start": True})
                async with lifespan_func():
                    yield

        # If no external server configuration, directly return user lifespan
        if not has_external_servers:
            return user_lifespan

        # If user didn't provide lifespan, directly use external server lifespan
        if not user_lifespan:
            return mount_lifespan

        # If both exist, need to combine them
        async def combined_lifespan(server: Any) -> Any:
            """Combine user lifespan and external server lifespan"""
            # First start external servers
            mount_gen = mount_lifespan(server)
            await mount_gen.__anext__()  # Start external servers

            try:
                # Then execute user lifespan
                user_gen = user_lifespan(server)
                await user_gen.__anext__()  # Start user lifespan

                try:
                    yield  # Server running period
                finally:
                    # First close user lifespan
                    with contextlib.suppress(StopAsyncIteration):
                        await user_gen.__anext__()
            finally:
                # Finally close external servers
                with contextlib.suppress(StopAsyncIteration):
                    await mount_gen.__anext__()

        return combined_lifespan

    def _add_components(self, server: ManagedServer, source: str | dict[str, Any] | Path) -> None:
        """Intelligently register components to the server

        Automatically handle different component directory structures by determining
        the appropriate base path based on source type.
        """
        config = getattr(server, "_config", {})
        components_config = config.get("components")
        if not components_config:
            return  # No component configuration

        if self._is_project_mode(source, config):
            # Project mode: delegate to ComponentManager
            project_path = self._determine_project_path(source)
            if project_path:
                from .project.components import ComponentManager

                ComponentManager.register_components(server, project_path)
        else:
            # Configuration file mode: Factory handles shared-components
            self._register_shared_components(server, components_config)

    def _determine_project_path(self, source: str | dict[str, Any] | Path) -> Path | None:
        """Determine project path from source"""
        if isinstance(source, str | Path):
            source_path = Path(source)
            return source_path.parent if source_path.is_file() else source_path
        return None

    def _register_shared_components(self, server: ManagedServer, components_config: dict[str, Any]) -> None:
        """Register shared components to server

        Args:
            server: Server instance
            components_config: Component configuration dictionary
        """
        shared_components_path = self.workspace_root / "shared-components"

        for component_type in ["tools", "resources", "prompts"]:
            modules = components_config.get(component_type, [])
            for module_config in modules:
                if module_config.get("enabled", True):
                    module_name = module_config["module"]
                    module_path = shared_components_path / component_type / f"{module_name}.py"

                    if module_path.exists():
                        # Reuse ComponentManager's file loading logic
                        from .project.components import ComponentManager

                        functions = ComponentManager._load_component_functions_from_file(module_path)
                        ComponentManager._register_functions_to_server(server, component_type, functions)

    def _is_project_mode(self, source: Any, config: dict[str, Any]) -> bool:
        """Determine if the source represents project mode

        Args:
            source: Configuration source (file path, directory path, or dict)
            config: Configuration dictionary

        Returns:
            True if this is project mode, False for configuration file mode
        """
        from pathlib import Path

        # If source is a dictionary, it's configuration file mode
        if isinstance(source, dict):
            return False

        # If source is a path
        if isinstance(source, str | Path):
            source_path = Path(source)

            # If it's a directory, it's project mode
            if source_path.exists() and source_path.is_dir():
                return True

        # Default to configuration file mode
        return False

    def _complete_operation(self, server_id: str, event: str, log_message: str) -> None:
        """Complete operation logging and state update"""
        self._state_manager.record_server_event(server_id, event)
        logger.info(log_message, server_id)

    def _extract_current_server_config(self, server: ManagedServer, server_id: str | None = None) -> dict[str, Any]:
        """Extract current configuration state of server

        Args:
            server: Server instance

        Returns:
            dict: Current configuration state, including runtime changes
        """
        # Get base configuration
        base_config = getattr(server, "_config", {}).copy()

        # Ensure basic structure exists
        if "server" not in base_config:
            base_config["server"] = {}

        # Prioritize values from configuration object, use server attributes as fallback if not present
        # Note: Server attributes may be read-only, but values in configuration object may be modified at runtime
        if "name" not in base_config["server"]:
            base_config["server"]["name"] = server.name
        if "instructions" not in base_config["server"]:
            base_config["server"]["instructions"] = server.instructions
        if "expose_management_tools" not in base_config["server"]:
            base_config["server"]["expose_management_tools"] = getattr(server, "expose_management_tools", True)

        # Add project path information if available (use source_path for project directories)
        if server_id:
            project_path = self._get_server_project_path(server_id)
            if project_path:
                base_config["project_path"] = project_path

        # TODO: This can be extended to extract more runtime state
        # Such as mounting information, dynamically added tools, resources, etc. For now, implement basic functionality

        return base_config

    def _prepare_middleware(self, config: dict[str, Any]) -> list[Any] | None:
        """Prepare middleware instances from configuration

        Args:
            config: Server configuration

        Returns:
            List of middleware instances or None
        """
        from .middleware import load_middleware_from_config

        return load_middleware_from_config(config)

    # =========================================================================
    # Shared Components Management
    # =========================================================================

    def create_shared_component(
        self, component_type: str, component_name: str, functions: list[dict[str, Any]]
    ) -> Path:
        """Create shared component file

        Args:
            component_type: Component type (tools, resources, prompts)
            component_name: Component name
            functions: Function definition list

        Returns:
            Created component file path

        Raises:
            ValueError: When component type is invalid
        """
        from .project import ALLOWED_MODULE_TYPES

        if component_type not in ALLOWED_MODULE_TYPES:
            raise ValueError(f"Invalid component type: {component_type}. Must be one of {ALLOWED_MODULE_TYPES}")

        logger.info("Creating shared component: %s/%s", component_type, component_name)

        # Ensure shared component directory structure exists
        shared_components_path = self._ensure_shared_components_structure()

        # Create specific component file
        component_file_path = shared_components_path / component_type / f"{component_name}.py"

        # If file already exists, warn but continue
        if component_file_path.exists():
            logger.warning("Component file already exists: %s", component_file_path)

        # Generate component file content
        content_lines = [f"# {component_name.title()} - {component_type} module"]
        content_lines.append("# Generated by MCP Factory")
        content_lines.append("")

        # Collect all function names for __all__
        function_names = [func["name"] for func in functions]
        content_lines.append(f"__all__ = {function_names}")
        content_lines.append("")

        # Generate each function
        for func_info in functions:
            function_name = func_info["name"]
            description = func_info["description"]
            template_data = func_info.get("template_data", {})

            # Generate function code
            function_code = self._generate_shared_component_function(
                component_type, function_name, description, template_data
            )
            content_lines.append(function_code)
            content_lines.append("")  # Function spacing

        # Write to file
        component_file_path.write_text("\n".join(content_lines), encoding="utf-8")

        logger.info("Shared component created successfully: %s", component_file_path)
        return component_file_path

    def _generate_shared_component_function(
        self, component_type: str, function_name: str, description: str, template_data: dict[str, Any]
    ) -> str:
        """Generate shared component function code - reusing Builder's mature logic

        Args:
            component_type: Component type
            function_name: Function name
            description: Function description
            template_data: Template data

        Returns:
            Generated function code string
        """
        from .project import Builder

        # Reuse Builder's mature function code generation logic
        builder = Builder(str(self.workspace_root))
        return builder._generate_function_code(component_type, function_name, description, template_data)

    def list_shared_components(self) -> dict[str, list[dict[str, Any]]]:
        """List existing shared components

        Returns:
            Dictionary of component information grouped by type
        """
        from .project import ALLOWED_MODULE_TYPES

        shared_components_path = self.workspace_root / "shared-components"
        if not shared_components_path.exists():
            return {component_type: [] for component_type in ALLOWED_MODULE_TYPES}

        components: dict[str, list[dict[str, Any]]] = {component_type: [] for component_type in ALLOWED_MODULE_TYPES}

        for component_type in ALLOWED_MODULE_TYPES:
            type_dir = shared_components_path / component_type
            if type_dir.exists() and type_dir.is_dir():
                for py_file in type_dir.glob("*.py"):
                    if py_file.name == "__init__.py":
                        continue

                    component_info = {
                        "name": py_file.stem,
                        "file": py_file.name,
                        "type": component_type,
                        "path": str(py_file),
                        "functions": self._extract_functions_from_file(py_file),
                    }

                    components[component_type].append(component_info)

        return components

    def _ensure_shared_components_structure(self) -> Path:
        """Ensure shared component directory structure exists

        Returns:
            Shared component root directory path
        """
        from .project import ALLOWED_MODULE_TYPES

        shared_components_path = self.workspace_root / "shared-components"
        shared_components_path.mkdir(parents=True, exist_ok=True)

        # Create directory and __init__.py for each component type
        for component_type in ALLOWED_MODULE_TYPES:
            type_dir = shared_components_path / component_type
            type_dir.mkdir(parents=True, exist_ok=True)

            init_file = type_dir / "__init__.py"
            if not init_file.exists():
                init_file.write_text(f"# Shared {component_type} module\n", encoding="utf-8")

        logger.debug("Shared components structure ensured: %s", shared_components_path)
        return shared_components_path

    def _extract_functions_from_file(self, file_path: Path) -> list[str]:
        """Extract function name list from file

        Args:
            file_path: Python file path

        Returns:
            Function name list
        """
        import re

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # First try to extract from __all__
            all_match = re.search(r"__all__\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if all_match:
                exports = all_match.group(1)
                function_names = re.findall(r'["\']([^"\']+)["\']', exports)
                if function_names:
                    return function_names

            # If no __all__, scan function definitions
            function_pattern = r"^def (\w+)\("
            return re.findall(function_pattern, content, re.MULTILINE)

        except Exception as e:
            logger.debug("Failed to extract functions from %s: %s", file_path, e)
            return []

    # =========================================================================
    # Internal Methods - State Persistence
    # =========================================================================

    def _save_servers_state(self) -> None:
        """State is automatically managed by ServerStateManager"""
        # ServerStateManager automatically saves state when updates occur
        pass

    def _load_servers_state(self) -> None:
        """Load server instances from state manager"""
        try:
            # Get server summary from state manager
            servers_summary = self._state_manager.get_servers_summary()

            loaded_count = 0
            for server_id, server_state in servers_summary.items():
                try:
                    server = self._create_server_from_state_data(server_id, server_state)
                    self._servers[server_id] = server
                    loaded_count += 1
                except Exception as e:
                    logger.error("Failed to restore server %s: %s", server_id, e)

            if loaded_count > 0:
                logger.info("Server restoration completed: %s servers loaded", loaded_count)

        except Exception as e:
            logger.error("Failed to load servers from state manager: %s", e)

    def _create_server_from_state_data(self, server_id: str, server_state: dict[str, Any]) -> ManagedServer:
        """Rebuild server instance from state data"""
        try:
            # Get server basic information
            server_name = server_state.get("name", "")
            source_type = server_state.get("source_type", "unknown")
            source_path = server_state.get("source_path")

            # Get configuration information
            config = self._state_manager.get_server_config(server_id)
            if not config:
                # Unable to get configuration, skip this server
                raise ValueError(
                    f"Unable to restore server '{server_name}' ({server_id}): No configuration available. This may be an old format server."
                )

            # Extract server configuration
            server_config = config.get("server", {})
            server_params = {
                "name": server_name,
                "instructions": server_config.get("instructions", ""),
                "expose_management_tools": server_config.get("expose_management_tools", True),
            }

            # If configuration has external servers, prepare lifecycle
            mount_lifespan = self._prepare_lifespan(config, None)
            if mount_lifespan:
                server_params["lifespan"] = mount_lifespan

            server = ManagedServer(**server_params)
            server._server_id = server_id
            server._config = config
            server._created_at = server_state.get("created_at", "")

            # Restore project components (if it's a project directory)
            if source_type == "project_dir" and source_path:
                project_path = Path(source_path)
                if project_path.exists() and project_path.is_dir():
                    ComponentManager.register_components(server, project_path)

            return server
        except Exception as e:
            self._error_handler.handle_error("Failed to rebuild server from state data", e, {"server_id": server_id})
            raise  # Re-raise exception to maintain type consistency
