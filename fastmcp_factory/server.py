"""FastMCP server extension module, providing the ManagedServer class.

This module provides the ManagedServer class for creating and managing servers with enhanced
functionality. It contains extended classes for FastMCP, offering more convenient management
of tools and configurations.
"""

import inspect
import warnings
from typing import Any, Callable, Dict, Optional, TypeVar

from fastmcp import FastMCP
from mcp.server.auth.provider import OAuthAuthorizationServerProvider

# Define common types
AnyFunction = Callable[..., Any]
LifespanResultT = TypeVar("LifespanResultT")


class ManagedServer(FastMCP):
    """ManagedServer extends FastMCP to provide additional management capabilities.

    Note: All management tools are prefixed with "manage_" to allow frontend or callers
    to easily filter management tools. For example, the mount method of FastMCP
    would be registered as "manage_mount".
    """

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

    def __init__(
        self,
        name: str,
        instructions: str = "",
        auto_register: bool = True,
        auth_server_provider: Optional[OAuthAuthorizationServerProvider[Any, Any, Any]] = None,
        auth: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a ManagedServer.

        Args:
            name: Server name
            instructions: Server instructions
            auto_register: Whether to automatically register FastMCP's public methods as tools
            auth_server_provider: OAuth authentication service provider (recommended)
            auth: Authentication configuration
            **kwargs: Other parameters, will be used in the run method

        Important: When auto_register=True, it is strongly recommended to configure
        the auth_server_provider parameter.

        Note: According to FastMCP 2.3.4+ recommendations, runtime and transport-specific
        settings should be provided when calling run() or run_async(), not in the constructor.
        """
        super().__init__(name=name, instructions=instructions)

        if auth_server_provider:
            self._auth_server_provider = auth_server_provider

        if auth:
            self._auth = auth

        self._runtime_kwargs = kwargs.copy()

        has_provider = hasattr(self, "_auth_server_provider") and self._auth_server_provider
        if auto_register and not has_provider:
            warnings.warn(
                "Management tool auto-registration enabled without authentication. "
                "This may allow unauthorized users to access sensitive functions. "
                "Configure auth_server_provider parameter.",
                UserWarning,
                stacklevel=2,
            )

        if auto_register:
            self._auto_register_management_tools()

    # Public methods

    def run(self, transport: Optional[str] = None, **kwargs: Dict[str, Any]) -> Any:
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
        runtime_kwargs = {**self._runtime_kwargs, **kwargs}

        if hasattr(self, "_auth_server_provider") and self._auth_server_provider:
            runtime_kwargs["auth_server_provider"] = self._auth_server_provider

        if hasattr(self, "_auth") and self._auth:
            runtime_kwargs["auth"] = self._auth

        # Call the base class run method
        if transport:
            return super().run(transport=transport, **runtime_kwargs)
        else:
            return super().run(**runtime_kwargs)

    def reload_config(self, config_path: Optional[str] = None) -> str:
        """Reload server configuration from file.

        Args:
            config_path: Optional path to configuration file. If None, the default path is used.

        Returns:
            A message indicating the result of the reload operation

        Example:
            server.reload_config()
            server.reload_config("/path/to/new_config.json")
        """
        try:
            if config_path:
                print(f"Attempting to load configuration from {config_path}...")
                self._load_config_from_file(config_path)
            else:
                self._load_default_config()

            msg_part = f" (from {config_path})" if config_path else ""
            return f"Server configuration reloaded{msg_part}"
        except Exception as e:
            error_msg = f"Configuration reload failed: {str(e)}"
            print(error_msg)
            return error_msg

    # Private methods

    def _auto_register_management_tools(self) -> None:
        """Automatically scan and register FastMCP's public methods as management tools."""
        try:
            annotations = {
                "title": "Management Tool",
                "destructiveHint": True,
                "requiresAuth": True,
                "adminOnly": True,
            }

            registered_count = 0

            # Scan all public methods of FastMCP class
            for name, method in inspect.getmembers(FastMCP, predicate=inspect.isfunction):
                if name.startswith("_") or name in self.EXCLUDED_METHODS:
                    continue

                if not hasattr(self, name):
                    continue

                instance_method = getattr(self, name)
                try:
                    sig = inspect.signature(instance_method)
                    has_var_args = any(
                        p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
                        for p in sig.parameters.values()
                    )
                    if has_var_args:
                        continue

                    # Get parameter names except 'self'
                    param_names = [p for p in sig.parameters if p != "self"]
                    is_async = inspect.iscoroutinefunction(instance_method)
                    params_str = ", ".join(param_names)
                    locals_dict = {"self": self, "method": instance_method}

                    if is_async:
                        async_code = (
                            f"async def wrapper({params_str}):\n"
                            f'    """Management Tool: {name}"""\n'
                            f"    return await method({params_str})\n"
                        )
                        exec(async_code, {}, locals_dict)
                        wrapper = locals_dict["wrapper"]
                    else:
                        sync_code = (
                            f"def wrapper({params_str}):\n"
                            f'    """Management Tool: {name}"""\n'
                            f"    return method({params_str})\n"
                        )
                        exec(sync_code, {}, locals_dict)
                        wrapper = locals_dict["wrapper"]

                    doc = instance_method.__doc__ or f"{name} method"
                    description = doc.split("\n")[0] if doc else f"{name} method"
                    self.tool(
                        name=f"manage_{name}", description=description, annotations=annotations
                    )(wrapper)

                    registered_count += 1
                except Exception as e:
                    print(f"Error registering method {name}: {e}")

            # Register custom reload_config method
            if hasattr(self, "reload_config"):

                def wrapped_reload_config(config_path: Optional[str] = None) -> str:
                    """Management Tool: Reload server configuration."""
                    return self.reload_config(config_path)

                self.tool(
                    name="manage_reload_config",
                    description="Reload server configuration",
                    annotations=annotations,
                )(wrapped_reload_config)

                registered_count += 1

            print(f"Automatically registered {registered_count} management tools")

        except Exception as e:
            print(f"Error during auto-registration of management tools: {e}")

    def _load_config_from_file(self, config_path: str) -> dict:
        """Load configuration from a file.

        Args:
            config_path: Path to configuration file

        Returns:
            The loaded configuration

        Raises:
            FileNotFoundError: When file doesn't exist
            ValueError: When configuration format is invalid
            Exception: Other loading errors
        """
        # For example: Read JSON, YAML, etc. configuration file
        print(f"(Simulated) Loading configuration from {config_path}...")
        return {}

    def _load_default_config(self) -> dict:
        """Load configuration from default location.

        Returns:
            The loaded configuration

        Raises:
            FileNotFoundError: When default configuration file doesn't exist
            ValueError: When configuration format is invalid
            Exception: Other loading errors
        """
        # For example: Load config.json from current directory or user home
        return {}
