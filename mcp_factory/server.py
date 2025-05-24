"""FastMCP server extension module, providing the ManagedServer class.

This module provides the ManagedServer class for creating and managing servers with enhanced
functionality. It contains extended classes for FastMCP, offering more convenient management
of tools and configurations.
"""

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

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

    ############################
    # Initialization
    ############################

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
        """Initialize Managed Server with extended capabilities.

        Args:
            name: Server name
            instructions: Server instructions
            expose_management_tools: Whether to expose management tools
            auth_server_provider: OAuth Authorization Server provider
            auth: Authentication configuration
            lifespan: Optional lifespan context manager for the server
            tags: Tags for this server
            dependencies: Dependencies for this server
            tool_serializer: Tool serializer
            **kwargs: Extra arguments passed to FastMCP
        """
        # Check and remove unsupported fastmcp parameters
        if "streamable_http_path" in kwargs:
            logger.warning("FastMCP does not support streamable_http_path parameter, removed")
            kwargs.pop("streamable_http_path")

        # Separate runtime parameters and constructor parameters to avoid FastMCP 2.3.4+ deprecation warnings
        runtime_params = {}
        constructor_params = {}

        # Define runtime parameters (these parameters should be passed during run())
        runtime_param_names = {
            "host",
            "port",
            "transport",
            "debug",
            "cors_origins",
            "cors_methods",
            "cors_headers",
            "cors_credentials",
            "max_request_size",
            "timeout",
            "keep_alive",
        }

        # Define parameters supported by FastMCP constructor
        fastmcp_constructor_params = {
            "cache_expiration_seconds",
            "on_duplicate_tools",
            "on_duplicate_resources",
            "on_duplicate_prompts",
            "resource_prefix_format",
        }

        # Define ManagedServer-specific parameters (should not be passed to FastMCP)
        managed_server_params = {"expose_management_tools"}

        # Separate parameters
        for key, value in kwargs.items():
            if key in runtime_param_names:
                runtime_params[key] = value
            elif key in managed_server_params:
                # ManagedServer-specific parameters, already handled in method parameters, do not pass to FastMCP
                pass
            elif key in fastmcp_constructor_params:
                # Parameters supported by FastMCP constructor
                constructor_params[key] = value
            else:
                # Other unknown parameters, log warning and add to runtime parameters
                logger.warning(f"Unknown parameter '{key}', treating as runtime parameter")
                runtime_params[key] = value

        # Initialize base class (only pass constructor parameters)
        # FastMCP 2.4.0 requires auth_server_provider and settings.auth to exist together or not exist together
        # Although there will be deprecation warnings, this is necessary validation
        auth_settings = {}
        if auth is not None:
            auth_settings["auth"] = auth

        super().__init__(
            name=name,
            instructions=instructions,
            auth_server_provider=auth_server_provider,
            lifespan=lifespan,
            tags=tags,
            dependencies=dependencies,
            tool_serializer=tool_serializer,
            **constructor_params,
            **auth_settings,
        )

        # Initialize configuration
        self._config = {}
        self._current_user = None
        # Save runtime parameters for use during run()
        self._runtime_kwargs = runtime_params

        # Also save auth configuration in runtime parameters for backup
        if auth is not None:
            self._runtime_kwargs["auth"] = auth

        # If expose_management_tools is set, automatically register management tools
        if expose_management_tools:
            self._expose_management_tools()

    ############################
    # Public Interface Methods
    ############################

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

    ############################
    # Management Tools Methods
    ############################

    def _expose_management_tools(self) -> None:
        """Register management tools in two categories.

        1. Native management tools: FastMCP native methods
        2. Extension management tools: Our extended functionality
        """
        try:
            logger.info("Starting management tools registration...")

            # Register native management tools (FastMCP native methods)
            native_count = self._register_native_management_tools()

            # Register extension management tools (our functionality extensions)
            logger.info("Starting extension management tools registration...")
            extension_count = 0

            # Check if tool already exists
            tool_name = "manage_reload_config"
            existing_tools = getattr(self._tool_manager, "_tools", {})
            if tool_name not in existing_tools:
                try:
                    # Create tool function
                    def reload_func(config_path: Optional[str] = None) -> str:
                        """Reload server configuration.

                        Args:
                            config_path: Optional configuration file path

                        Returns:
                            Result message
                        """
                        return self.reload_config(config_path)

                    # Register tool
                    self.tool(
                        name=tool_name,
                        description="Reload server configuration",
                        annotations=self.MANAGEMENT_TOOL_ANNOTATIONS,
                    )(reload_func)

                    extension_count = 1
                    logger.debug(f"Registered extension tool: {tool_name}")

                except Exception as e:
                    logger.error(f"Failed to register extension tool {tool_name}: {str(e)}")
            else:
                logger.warning(f"Extension tool already exists, skipping registration: {tool_name}")

            logger.info(
                f"Extension management tools registration completed: {extension_count} successful"
            )

            total_count = native_count + extension_count

            logger.info(
                f"Management tools registration completed: {native_count} native tools, {extension_count} extension tools, {total_count} total"
            )

        except Exception as e:
            logger.error(f"Error occurred during management tools registration: {e}")
            import traceback

            logger.debug(f"Error details: {traceback.format_exc()}")

    def _register_native_management_tools(self) -> int:
        """Register FastMCP native methods as management tools.

        Returns:
            Number of successfully registered native tools
        """
        logger.info("Starting native management tools registration (FastMCP native methods)...")
        registered_count = 0
        failed_count = 0

        # Get all members of FastMCP base class
        from fastmcp import FastMCP

        for name, member in inspect.getmembers(FastMCP):
            # Skip private methods, excluded methods, and non-function members
            if (
                name.startswith("_")
                or name in self.EXCLUDED_METHODS
                or not inspect.isfunction(member)
            ):
                continue

            # Check if tool name already exists
            tool_name = f"manage_{name}"
            existing_tools = getattr(self._tool_manager, "_tools", {})
            if tool_name in existing_tools:
                logger.debug(f"Native tool already exists, skipping registration: {tool_name}")
                continue

            try:
                # Try to register directly, let FastMCP handle compatibility itself
                logger.debug(f"Registering native management tool: {tool_name}")
                original_func = getattr(self, name)

                # Try to get function signature, use generic wrapper if failed
                try:
                    sig = inspect.signature(original_func)

                    # Create management tool wrapper function
                    # Get non-self parameters
                    non_self_params = [p for p in sig.parameters.values() if p.name != "self"]
                    param_count = len(non_self_params)

                    # Create wrapper based on parameter count
                    if param_count == 0:

                        def wrapper() -> Any:
                            return self._execute_wrapped_function(original_func, name, ())
                    elif param_count == 1:

                        def wrapper(arg1: Any) -> Any:
                            return self._execute_wrapped_function(original_func, name, (arg1,))
                    elif param_count == 2:

                        def wrapper(arg1: Any, arg2: Any) -> Any:
                            return self._execute_wrapped_function(original_func, name, (arg1, arg2))
                    elif param_count == 3:

                        def wrapper(arg1: Any, arg2: Any, arg3: Any) -> Any:
                            return self._execute_wrapped_function(
                                original_func, name, (arg1, arg2, arg3)
                            )
                    else:
                        # For functions with more than 3 parameters, use a generic wrapper
                        logger.debug(
                            f"Function {name} has {param_count} parameters, using generic wrapper"
                        )

                        def wrapper() -> Any:
                            return self._execute_wrapped_function(original_func, name, ())

                    # Set function metadata
                    wrapper.__name__ = original_func.__name__
                    wrapper.__doc__ = original_func.__doc__ or f"Management wrapper for {name}"
                    wrapper.__module__ = original_func.__module__
                    wrapped_func = wrapper

                except Exception:
                    # If unable to get signature, create a simple generic wrapper
                    def simple_wrapper() -> Any:
                        return self._execute_wrapped_function(original_func, name, ())

                    simple_wrapper.__name__ = original_func.__name__
                    simple_wrapper.__doc__ = (
                        original_func.__doc__ or f"Management wrapper for {name}"
                    )
                    simple_wrapper.__module__ = original_func.__module__
                    wrapped_func = simple_wrapper

                # Register as tool
                self.tool(
                    name=tool_name,
                    description=f"Native management function: {name}",
                    annotations=self.MANAGEMENT_TOOL_ANNOTATIONS,
                )(wrapped_func)

                registered_count += 1

            except Exception as e:
                logger.warning(f"Failed to register native tool {name}: {str(e)}")
                failed_count += 1

        logger.info(
            f"Native management tools registration completed: {registered_count} successful, {failed_count} failed"
        )
        return registered_count

    def _execute_wrapped_function(self, func: AnyFunction, name: str, args: tuple) -> Any:
        """Execute wrapped function with common logic

        Args:
            func: Original function
            name: Function name
            args: Parameter tuple

        Returns:
            Function execution result
        """
        # Get caller information
        caller_info = ""
        caller_user = getattr(self, "_current_user", None)
        if caller_user:
            caller_info = f" [User: {caller_user.get('id', 'Unknown')}]"

        # Format parameter information
        if args:
            args_str = ", ".join(str(arg) for arg in args)
            logger.info(f"Management tool call: {name}{caller_info} | Parameters: {args_str}")
        else:
            logger.info(f"Management tool call: {name}{caller_info} | No parameters")

        try:
            # Execute function
            if args:
                result = func(self, *args)
            else:
                result = func(self)

            logger.info(f"Management tool {name} executed successfully")
            return result

        except Exception as e:
            logger.error(f"Management tool {name} execution failed: {str(e)}")
            raise

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
                for name in getattr(self._tool_manager, "_tools", {}).keys()
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

    ############################
    # Configuration Methods
    ############################

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
                try:
                    # Get all non-management tools
                    all_tools = [
                        name
                        for name in getattr(self._tool_manager, "_tools", {}).keys()
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

        # Process tool permissions configuration
        if "tool_permissions" in tools_config:
            tool_permissions = tools_config["tool_permissions"]
            if isinstance(tool_permissions, dict):
                try:
                    tools_updated = 0

                    # Iterate over permission configuration
                    for tool_name, permissions in tool_permissions.items():
                        if not isinstance(permissions, dict):
                            continue

                        # Get tool
                        tool = getattr(self._tool_manager, "_tools", {}).get(tool_name)
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

        try:
            # Extract advanced configuration
            advanced_config = param_utils.extract_config_section(self._config, "advanced")
            if not advanced_config:
                return

            # Use tool functions to handle advanced parameters
            param_utils.apply_advanced_params(self, advanced_config, self._runtime_kwargs)
            logger.debug("Applied advanced configuration parameters")
        except Exception as e:
            logger.error(f"Error applying advanced configuration: {e}")
            # Continue gracefully without crashing the server

    ############################
    # Runtime Parameter Methods
    ############################

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
        runtime_kwargs = (
            getattr(self, "_runtime_kwargs", {}).copy() if hasattr(self, "_runtime_kwargs") else {}
        )

        # Next, extract runtime-related parameters from configuration (if any)
        if hasattr(self, "_config") and self._config:
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

        # Avoid repeated transport parameter passing
        if "transport" in runtime_kwargs and transport is not None:
            logger.warning(f"Detected repeated transport parameter, using: {transport}")
            runtime_kwargs.pop("transport", None)

        # Handle FastMCP base class unsupported advanced parameters
        if "streamable_http_path" in runtime_kwargs:
            path = runtime_kwargs.pop("streamable_http_path")
            logger.warning(
                f"Removing unsupported parameter streamable_http_path: {path} (note: this parameter does not work in FastMCP)"
            )

        # Remove debug parameter as FastMCP doesn't support it
        if "debug" in runtime_kwargs:
            debug_value = runtime_kwargs.pop("debug")
            logger.debug(
                f"Removing unsupported debug parameter: {debug_value} (FastMCP uses log_level instead)"
            )
            # Convert debug to log_level if needed
            if debug_value and "log_level" not in runtime_kwargs:
                runtime_kwargs["log_level"] = "debug"

        return transport, runtime_kwargs
