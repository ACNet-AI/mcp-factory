"""FastMCP server extension module, providing the ManagedServer class.

This module provides the ManagedServer class for creating and managing servers with enhanced
functionality. It contains extended classes for FastMCP, offering more convenient management
of tools and configurations.
"""

import inspect
import logging
import warnings
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar

from fastmcp import FastMCP
from mcp.server.auth.provider import OAuthAuthorizationServerProvider

# Import configuration validator and parameter utilities
from mcp_factory import config_validator, param_utils

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define common types
AnyFunction = Callable[..., Any]
LifespanResultT = TypeVar("LifespanResultT")


class ManagedServer(FastMCP):
    """ManagedServer extends FastMCP to provide additional management capabilities.

    Note: All management tools are prefixed with "manage_" to allow frontend or callers
    to easily filter management tools. For example, the mount method of FastMCP
    would be registered as "manage_mount".
    """

    # Management tool annotations
    MANAGEMENT_TOOL_ANNOTATIONS = {
        "title": "Management Tool",
        "destructiveHint": True,
        "requiresAuth": True,
        "adminOnly": True,
    }

    EXCLUDED_METHODS = {
        # Special methods (Python internal)
        "__init__",
        "__new__",
        "__call__",
        "__str__",
        "__repr__",
        "__getattribute__",
        "__setattr__",
        "__delattr__",
        "__dict__",
        # Runtime methods
        "run",
        "run_async",
    }

    #######################
    # Initialization
    #######################

    def __init__(
        self,
        name: str,
        instructions: str = "",
        expose_management_tools: bool = True,
        auth_server_provider: Optional[OAuthAuthorizationServerProvider[Any, Any, Any]] = None,
        auth: Optional[Dict[str, Any]] = None,
        lifespan: Optional[Callable[[Any], Any]] = None,
        tags: Optional[Set[str]] = None,
        dependencies: Optional[List[str]] = None,
        tool_serializer: Optional[Callable[[Any], str]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a ManagedServer.

        Args:
            name: Server name
            instructions: Server instructions
            expose_management_tools: Whether to expose FastMCP methods as management tools
            auth_server_provider: OAuth authentication service provider
            auth: Authentication configuration
            lifespan: Server lifespan context manager
            tags: Set of tags for this server
            dependencies: List of dependencies for this server
            tool_serializer: Function to serialize tool results
            **kwargs: Other parameters, will be used in the run method

        Note: When expose_management_tools=True, it is strongly recommended to configure
        the auth_server_provider parameter.
        """
        # Pass advanced parameters to FastMCP constructor
        super().__init__(
            name=name,
            instructions=instructions,
            lifespan=lifespan,
            tags=tags,
            dependencies=dependencies,
            tool_serializer=tool_serializer,
        )

        # Initialize configuration storage
        self._config = None
        self._runtime_kwargs = kwargs.copy()

        # Set authentication provider
        if auth_server_provider:
            self._auth_server_provider = auth_server_provider

        # Set authentication configuration
        if auth:
            self._auth = auth

        # Auto-register management tools
        has_provider = hasattr(self, "_auth_server_provider") and self._auth_server_provider
        if expose_management_tools and not has_provider:
            warnings.warn(
                "Exposing FastMCP native methods as management tools without authentication. "
                "This may allow unauthorized users to access sensitive functions. "
                "While tools are configured to require authentication (requiresAuth=True) and "
                "administrator privileges (adminOnly=True), these restrictions cannot be enforced "
                "without a properly configured auth_server_provider parameter.",
                UserWarning,
                stacklevel=2,
            )

        if expose_management_tools:
            self._expose_management_tools()

    #######################
    # Public Methods
    #######################

    def run(self, transport: Optional[str] = None, **kwargs: Any) -> Any:
        """Run the server with the specified transport.

        Args:
            transport: Transport mode ("stdio", "sse", or "streamable-http")
            **kwargs: Transport-related configuration, such as host, port, etc.

        Note: This method follows the FastMCP 2.3.4+ recommended practice
        of providing runtime and transport-specific settings in the run method,
        rather than in the constructor.

        Returns:
            The result of running the server
        """
        # Prepare runtime parameters
        transport, runtime_kwargs = self._prepare_runtime_params(transport, **kwargs)

        # Call the base class run method
        logger.info(f"Starting server with transport: {transport or 'default'}")
        if transport:
            return super().run(transport=transport, **runtime_kwargs)
        else:
            return super().run(**runtime_kwargs)

    def apply_config(self, config: Dict[str, Any]) -> None:
        """Apply configuration to the server.

        Args:
            config: Configuration dictionary (already validated)
        """
        logger.debug("Applying configuration...")

        # Save complete configuration
        self._config = config

        # Apply different configuration sections (simplified structure)
        self._apply_basic_configs()  # Combined basic configuration (server basic info and authentication)
        self._apply_tools_config()
        self._apply_advanced_config()

        logger.debug("Configuration applied")

    def reload_config(self, config_path: Optional[str] = None) -> str:
        """Reload server configuration from file.

        Args:
            config_path: Optional path to configuration file. If None, the default path is used.

        Returns:
            A message indicating the result of the reload operation

        Example:
            server.reload_config()
            server.reload_config("/path/to/server_config.yaml")
        """
        try:
            if config_path:
                logger.info(f"Loading configuration from {config_path}...")
                is_valid, config, errors = config_validator.validate_config_file(config_path)
                if not is_valid:
                    error_msg = f"Configuration loading failed: {'; '.join(errors)}"
                    logger.error(error_msg)
                    return error_msg
                self._config = config
            else:
                logger.info("Loading default configuration...")
                self._config = config_validator.get_default_config()

            # Apply configuration to server
            self.apply_config(self._config)

            msg_part = f" (from {config_path})" if config_path else ""
            success_msg = f"Server configuration reloaded{msg_part}"
            logger.info(success_msg)
            return success_msg
        except Exception as e:
            error_msg = f"Configuration reload failed: {str(e)}"
            logger.error(error_msg)
            return error_msg

    #######################
    # Private Methods - Tool Registration
    #######################

    def _expose_management_tools(self) -> None:
        """Register FastMCP native methods as management tools.

        This enables remote management of the server's functionality.
        All tools are prefixed with "manage_" to allow easy filtering.
        """
        try:
            registered_count = 0

            # Get all members of the current class (including inherited ones)
            for name, member in inspect.getmembers(self.__class__):
                # Skip private methods, excluded methods, and non-function members
                if (
                    name.startswith("_")
                    or name in self.EXCLUDED_METHODS
                    or not inspect.isfunction(member)
                ):
                    continue

                # Create wrapper functions for native methods and register as tools
                logger.debug(f"Registering management tool: manage_{name}")

                # Get original method signature and create wrapper function
                original_func = getattr(self, name)

                # Use custom function wrapper
                wrapped_func = self._create_management_wrapper(original_func, name)

                # Register as tool (using annotated decorator)
                self.tool(
                    name=f"manage_{name}",
                    description=f"Management function: {name}",
                    annotations=self.MANAGEMENT_TOOL_ANNOTATIONS,
                )(wrapped_func)

                registered_count += 1

            # Additional registration of special management tools
            self._register_special_management_tools()

            logger.info(
                f"Automatically registered {registered_count} management tools "
                f"with authentication requirements"
            )

        except Exception as e:
            logger.error(f"Error exposing management tools: {e}")

    def _create_management_wrapper(self, func: AnyFunction, name: str) -> AnyFunction:
        """Create management tool wrapper function for the original method.

        Args:
            func: Original method
            name: Method name

        Returns:
            Wrapped function
        """

        def wrapped_func(*args: Any, **kwargs: Any) -> Any:
            # Enhanced audit log
            caller_info = ""
            # Try to get caller information (if available)
            caller_user = getattr(self, "_current_user", None)
            if caller_user:
                caller_info = f" [User: {caller_user.get('id', 'Unknown')}]"

            # Record detailed log for management tool calls
            logger.info(f"Management tool call: {name}{caller_info} | Parameters: {args}, {kwargs}")

            try:
                result = func(*args, **kwargs)
                # Record execution result log
                logger.info(f"Management tool {name} executed successfully")
                return result
            except Exception as e:
                # Record execution failure log
                logger.error(f"Management tool {name} execution failed: {str(e)}")
                raise

        # Copy original function signature and docstring
        wrapped_func.__name__ = func.__name__
        wrapped_func.__doc__ = func.__doc__
        wrapped_func.__module__ = func.__module__

        # Return wrapped function
        return wrapped_func

    def _register_special_management_tools(self) -> None:
        """Register special management tools.

        These tools are not directly from FastMCP methods, but are specially created for managing the server.
        """

        # Register reload configuration tool
        @self.tool(
            name="manage_reload_config",
            description="Reload server configuration",
            annotations=self.MANAGEMENT_TOOL_ANNOTATIONS,
        )
        def wrapped_reload_config(config_path: Optional[str] = None) -> str:
            """Reload server configuration.

            Args:
                config_path: Optional path to configuration file

            Returns:
                Result message
            """
            return self.reload_config(config_path)

    def _clear_management_tools(self) -> int:
        """Clear all registered management tools.

        Returns:
            int: Number of cleared tools
        """
        try:
            # Get all tools
            removed_count = 0

            # Get snapshot of tool list (to avoid modifying set during iteration)
            tool_keys = [
                name
                for name in self.__dict__.get("_tools", {}).keys()
                if isinstance(name, str) and name.startswith("manage_")
            ]

            # Remove each management tool
            for tool_name in tool_keys:
                try:
                    self.remove_tool(tool_name)
                    removed_count += 1
                    logger.debug(f"Removed management tool: {tool_name}")
                except Exception as e:
                    logger.warning(f"Failed to remove tool {tool_name}: {e}")

            logger.info(f"Cleared {removed_count} management tools")

            # Update status flag
            self._management_tools_exposed = False

            return removed_count
        except Exception as e:
            logger.error(f"Error clearing management tools: {e}")
            return 0

    #######################
    # Private Methods - Configuration Application
    #######################

    def _apply_basic_configs(self) -> None:
        """Apply basic configuration parameters (server info and authentication)."""
        if not self._config:
            return

        # Extract server basic configuration
        server_config = param_utils.extract_config_section(self._config, "server")
        if server_config:
            # Note: name and instructions attributes are now read-only, cannot be set here, must be specified in constructor
            logger.debug(
                f"Found server configuration with name: {server_config.get('name', 'N/A')}"
            )

        # Extract and apply authentication configuration
        auth_config = param_utils.extract_config_section(self._config, "auth")
        if auth_config:
            self._auth = auth_config
            logger.debug("Applied authentication configuration")

    def _apply_tools_config(self) -> None:
        """Apply tools configuration.

        This method processes the tools configuration section of the configuration file.
        """
        if not self._config:
            return

        # Extract tools configuration
        tools_config = param_utils.extract_config_section(self._config, "tools")
        if not tools_config:
            return

        # Process management tools exposure option (expose_management_tools)
        expose_tools = tools_config.get("expose_management_tools")

        # If configured (not None) and different from current state, apply
        if expose_tools is not None:
            # Clear current tools (if needed to reapply)
            current_has_tools = hasattr(self, "_management_tools_exposed") and getattr(
                self, "_management_tools_exposed", False
            )
            if current_has_tools and not expose_tools:
                # Clear registered management tools
                self._clear_management_tools()

            # Register tools (if needed)
            if not current_has_tools and expose_tools:
                self._expose_management_tools()

            # Record application state
            self._management_tools_exposed = expose_tools
            logger.debug(f"Applied tools configuration: expose_management_tools = {expose_tools}")

        # Process tool enablement/disablement configuration
        if "enabled_tools" in tools_config:
            enabled_tools = tools_config["enabled_tools"]
            if isinstance(enabled_tools, list):
                self._apply_tool_enablement(enabled_tools)

        # Process tool permissions configuration
        if "tool_permissions" in tools_config:
            tool_permissions = tools_config["tool_permissions"]
            if isinstance(tool_permissions, dict):
                self._apply_tool_permissions(tool_permissions)

    def _apply_tool_enablement(self, enabled_tools: List[str]) -> None:
        """Apply tool enablement/disablement configuration.

        Args:
            enabled_tools: List of enabled tool names, other tools will be disabled
        """
        try:
            # Get all non-management tools
            all_tools = [
                name
                for name in self.__dict__.get("_tools", {}).keys()
                if isinstance(name, str) and not name.startswith("manage_")
            ]

            # Find tools to disable (tools not in enabled list)
            to_disable = [name for name in all_tools if name not in enabled_tools]

            # Disable tools
            for tool_name in to_disable:
                try:
                    self.remove_tool(tool_name)
                    logger.debug(f"Disabled tool: {tool_name}")
                except Exception as e:
                    logger.warning(f"Failed to disable tool {tool_name}: {e}")

            if to_disable:
                logger.info(f"Disabled {len(to_disable)} tools based on configuration")
        except Exception as e:
            logger.error(f"Error applying tool enablement: {e}")

    def _apply_tool_permissions(self, tool_permissions: Dict[str, Dict[str, Any]]) -> None:
        """Apply tool permissions configuration.

        Args:
            tool_permissions: Mapping of tool names to permission configurations
        """
        try:
            tools_updated = 0

            # Iterate over permission configuration
            for tool_name, permissions in tool_permissions.items():
                if not isinstance(permissions, dict):
                    continue

                # Get tool
                tool = self.__dict__.get("_tools", {}).get(tool_name)
                if not tool:
                    logger.warning(f"Cannot apply permissions: Tool {tool_name} not found")
                    continue

                # Update tool annotations
                current_annotations = getattr(tool, "annotations", {}) or {}
                updated_annotations = {**current_annotations, **permissions}

                # Apply updated annotations
                setattr(tool, "annotations", updated_annotations)
                tools_updated += 1
                logger.debug(f"Updated permissions for tool: {tool_name}")

            if tools_updated:
                logger.info(f"Updated permissions for {tools_updated} tools")
        except Exception as e:
            logger.error(f"Error applying tool permissions: {e}")

    def _apply_advanced_config(self) -> None:
        """Apply advanced configuration parameters.

        This method processes the advanced configuration section of the configuration file.
        """
        if not self._config:
            return

        # Extract advanced configuration
        advanced_config = param_utils.extract_config_section(self._config, "advanced")
        if not advanced_config:
            return

        # Use tool functions to handle advanced parameters
        param_utils.apply_advanced_params(self, advanced_config, self._runtime_kwargs)
        logger.debug("Applied advanced configuration parameters")

    #######################
    # Private Methods - Runtime Parameter Processing
    #######################

    def _prepare_runtime_params(
        self, transport: Optional[str] = None, **kwargs: Any
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Prepare runtime parameters.

        Integrate parameters from the following sources:
        1. Runtime parameters saved in the constructor
        2. Parameters from configuration file (if any)
        3. Parameters provided by run() method (highest priority)

        Args:
            transport: Transport mode
            **kwargs: Runtime keyword arguments

        Returns:
            Tuple: (transport, runtime_kwargs)
        """
        # First, merge saved runtime parameters
        runtime_kwargs = self._runtime_kwargs.copy()

        # Next, extract runtime-related parameters from configuration (if any)
        if self._config:
            # Apply server-related runtime parameters (host, port, transport, etc.)
            server_config = param_utils.extract_config_section(self._config, "server")
            for key in ["host", "port", "transport", "debug"]:
                if key in server_config and key not in kwargs:
                    runtime_kwargs[key] = server_config[key]

        # Finally, use parameters provided by run() method (highest priority)
        runtime_kwargs.update(kwargs)

        # Merge transport parameter
        if not transport:
            transport = runtime_kwargs.pop("transport", None)

        # Add authentication parameters (if any)
        self._add_auth_params(runtime_kwargs)

        return transport, runtime_kwargs

    def _add_auth_params(self, runtime_kwargs: Dict[str, Any]) -> None:
        """Add authentication-related parameters to runtime parameters.

        Args:
            runtime_kwargs: Runtime parameters dictionary
        """
        # If there is an authentication service provider, add to runtime parameters
        if hasattr(self, "_auth_server_provider") and self._auth_server_provider:
            runtime_kwargs["auth_server_provider"] = self._auth_server_provider

        # If there is an authentication configuration, add to runtime parameters
        if hasattr(self, "_auth") and self._auth:
            # Security check: Ensure not overwriting explicitly provided auth_server_provider
            if "auth_server_provider" not in runtime_kwargs:
                runtime_kwargs["auth"] = self._auth
