"""FastMCP Factory module.

This module contains the FastMCPFactory class for creating and managing ManagedServer instances.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional, Set

from mcp.server.auth.provider import OAuthAuthorizationServerProvider

from mcp_factory import config_validator, param_utils
from mcp_factory.auth import AuthProviderRegistry
from mcp_factory.server import ManagedServer

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FastMCPFactory:
    """FastMCPFactory for unified creation and management of ManagedServer instances."""

    #######################
    # Initialization
    #######################

    def __init__(self, factory_config_path: Optional[str] = None) -> None:
        """Initialize the FastMCP factory.

        Args:
            factory_config_path: Path to factory configuration file (optional)
        """
        self._servers: Dict[str, ManagedServer] = {}
        self._factory_config = None  # Type: Optional[Dict[str, Any]]
        self._auth_registry = AuthProviderRegistry()

        # Load factory configuration (if provided)
        if factory_config_path and os.path.exists(factory_config_path):
            try:
                is_valid, config, errors = config_validator.validate_config_file(
                    factory_config_path
                )
                if is_valid:
                    self._factory_config = config
                    logger.info(f"Factory configuration loaded: {factory_config_path}")
                else:
                    logger.warning(f"Invalid factory configuration: {'; '.join(errors)}")
            except Exception as e:
                logger.error(f"Failed to load factory configuration: {str(e)}")

    #######################
    # Server Creation and Management Methods
    #######################

    def create_managed_server(
        self,
        config_path: str,
        expose_management_tools: bool = True,
        auth_provider_id: Optional[str] = None,
        lifespan: Optional[Callable[[Any], Any]] = None,
        tags: Optional[Set[str]] = None,
        dependencies: Optional[List[str]] = None,
        tool_serializer: Optional[Callable[[Any], str]] = None,
        **override_params: Any,
    ) -> ManagedServer:
        """Create a ManagedServer instance.

        Args:
            config_path: Server configuration file path
            expose_management_tools: Whether to expose server management tools
            auth_provider_id: Authentication provider ID (optional)
            lifespan: Server lifecycle manager (constructor parameter)
            tags: Server tag set (constructor parameter, will be merged with configuration)
            dependencies: Server dependencies (constructor parameter, will be merged with configuration)
            tool_serializer: Tool result serializer (constructor parameter)
            **override_params: Parameters that override configuration, can include constructor and settings parameters

        Returns:
            Created ManagedServer instance

        Raises:
            ValueError: If configuration file is invalid or server creation fails
            FileNotFoundError: If configuration file does not exist

        Note:
            Parameter priority from high to low: API parameters > Configuration file > Default values
            For collection parameters such as tags and dependencies, they are merged with configuration rather than replaced
        """
        logger.info(f"Creating server from {config_path}...")

        # 1. Load and validate configuration
        is_valid, config, errors = config_validator.validate_config_file(config_path)
        if not is_valid:
            error_msg = f"Invalid server configuration: {'; '.join(errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 2. Prepare server parameters
        server_params = self._prepare_server_params(
            config=config,
            expose_management_tools=expose_management_tools,
            auth_provider_id=auth_provider_id,
            lifespan=lifespan,
            tags=tags,
            dependencies=dependencies,
            tool_serializer=tool_serializer,
            **override_params,
        )

        # 3. Create server instance
        try:
            server = ManagedServer(**server_params)

            # 4. Apply complete configuration
            server.apply_config(config)

            # 5. Save server reference
            self._servers[server_params["name"]] = server
            logger.info(f"Server created: {server_params['name']}")

            return server

        except Exception as e:
            error_msg = f"Failed to create server: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def get_server(self, server_name: str) -> Optional[ManagedServer]:
        """Get a created server instance.

        Args:
            server_name: Server name

        Returns:
            Found ManagedServer instance, or None if it doesn't exist
        """
        return self._servers.get(server_name)

    def list_servers(self) -> Dict[str, Dict[str, Any]]:
        """List all managed servers.

        Returns:
            Dictionary mapping server names to server information
        """
        servers_info = {}
        for name, server in self._servers.items():
            servers_info[name] = {
                "name": server.name,
                "instructions": server.instructions,
                "tags": list(server.tags) if hasattr(server, "tags") else [],
                "dependencies": server.dependencies if hasattr(server, "dependencies") else [],
            }
        return servers_info

    def delete_server(self, server_name: str) -> str:
        """Delete a server instance.

        Args:
            server_name: Name of the server to delete

        Returns:
            Message indicating the operation result

        Raises:
            ValueError: If the server does not exist
        """
        server = self._servers.get(server_name)
        if not server:
            msg = f"Server not found: {server_name}"
            logger.warning(msg)
            raise ValueError(msg)

        # Close server (cleanup work)
        # TODO: Implement graceful server shutdown

        # Remove from dictionary
        del self._servers[server_name]
        msg = f"Server deleted: {server_name}"
        logger.info(msg)
        return msg

    #######################
    # Authentication Provider Management Methods
    #######################

    def create_auth_provider(
        self, provider_id: str, provider_type: str, config: Dict[str, Any]
    ) -> Optional[OAuthAuthorizationServerProvider]:
        """Create an authentication provider.

        Args:
            provider_id: Provider ID
            provider_type: Provider type ("auth0", "oauth", etc.)
            config: Provider configuration

        Returns:
            Created authentication provider, or None if creation fails
        """
        return self._auth_registry.create_provider(
            provider_id=provider_id, provider_type=provider_type, config=config
        )

    def get_auth_provider(self, provider_id: str) -> Optional[OAuthAuthorizationServerProvider]:
        """Get an authentication provider.

        Args:
            provider_id: Provider ID

        Returns:
            Found authentication provider, or None if it doesn't exist
        """
        return self._auth_registry.get_provider(provider_id)

    def list_auth_providers(self) -> Dict[str, str]:
        """List all authentication providers.

        Returns:
            Dictionary mapping provider IDs to provider types
        """
        return self._auth_registry.list_providers()

    def remove_auth_provider(self, provider_id: str) -> bool:
        """Remove an authentication provider.

        Args:
            provider_id: Provider ID

        Returns:
            Whether removal was successful
        """
        return self._auth_registry.remove_provider(provider_id)

    #######################
    # Internal Parameter Processing Methods
    #######################

    def _prepare_server_params(
        self,
        config: Dict[str, Any],
        expose_management_tools: bool = True,
        auth_provider_id: Optional[str] = None,
        lifespan: Optional[Callable[[Any], Any]] = None,
        tags: Optional[Set[str]] = None,
        dependencies: Optional[List[str]] = None,
        tool_serializer: Optional[Callable[[Any], str]] = None,
        **override_params: Any,
    ) -> Dict[str, Any]:
        """Prepare all parameters needed for server creation.

        1. Extract and apply basic server parameters
        2. Parse and apply authentication provider
        3. Process advanced parameters (including tags and dependencies merging)
        4. Apply runtime parameters and management tools settings

        Args:
            config: Validated configuration dictionary
            expose_management_tools: Whether to expose management tools
            auth_provider_id: Authentication provider ID
            lifespan: Server lifecycle manager
            tags: Server tag set
            dependencies: Server dependencies list
            tool_serializer: Tool result serializer
            **override_params: Override parameters

        Returns:
            Dictionary of parameters needed for server constructor
        """
        try:
            # 1. Extract server basic information
            server_config = param_utils.extract_config_section(config, "server")
            server_params = self._extract_base_params(server_config, override_params)

            # 2. Process authentication provider
            auth_server_provider = self._resolve_auth_provider(config, auth_provider_id)
            if auth_server_provider:
                server_params["auth_server_provider"] = auth_server_provider

            # Check if auth_server_provider was passed through override_params
            if "auth_server_provider" in override_params:
                server_params["auth_server_provider"] = override_params["auth_server_provider"]

            # If auth_server_provider exists (from any source), also pass auth configuration
            if "auth_server_provider" in server_params:
                # Also pass auth configuration (FastMCP 2.3.4+ requirement)
                auth_config = param_utils.extract_config_section(config, "auth")
                if auth_config:
                    server_params["auth"] = auth_config

            # 3. Process advanced parameters
            advanced_params = self._process_advanced_params(
                config=config,
                lifespan=lifespan,
                tags=tags,
                dependencies=dependencies,
                tool_serializer=tool_serializer,
            )
            server_params.update(advanced_params)

            # 4. Set management tools options and other runtime parameters
            server_params["expose_management_tools"] = expose_management_tools

            # Add other runtime parameters (parameters that are not in server section and override)
            runtime_params = {k: v for k, v in override_params.items() if k not in server_config}
            server_params.update(runtime_params)

            return server_params

        except Exception as e:
            error_msg = f"Error preparing server parameters: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _extract_base_params(
        self, server_config: Dict[str, Any], override_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract basic server parameters.

        Args:
            server_config: Server configuration section
            override_params: Override parameters

        Returns:
            Basic parameters dictionary
        """
        # Necessary basic parameters
        required_keys = ["name"]
        for key in required_keys:
            if key not in server_config and key not in override_params:
                raise ValueError(f"Missing required parameter: {key}")

        params = {}

        # Basic information parameters
        base_params = ["name", "instructions"]
        for key in base_params:
            # Use override parameters first
            if key in override_params:
                params[key] = override_params[key]
            # Use configuration parameters next
            elif key in server_config:
                params[key] = server_config[key]

        return params

    def _resolve_auth_provider(
        self, config: Dict[str, Any], auth_provider_id: Optional[str]
    ) -> Optional[OAuthAuthorizationServerProvider]:
        """Resolve authentication provider.

        Args:
            config: Configuration dictionary
            auth_provider_id: API specified authentication provider ID

        Returns:
            Resolved authentication provider or None
        """
        # First check API parameters
        if auth_provider_id:
            provider = self._auth_registry.get_provider(auth_provider_id)
            if provider:
                logger.debug(f"Using auth provider from parameter: {auth_provider_id}")
                return provider
            else:
                logger.warning(f"Auth provider not found: {auth_provider_id}")

        # Then check provider_id in configuration file
        auth_config = param_utils.extract_config_section(config, "auth")
        if auth_config and "provider_id" in auth_config:
            config_provider_id = auth_config["provider_id"]
            provider = self._auth_registry.get_provider(config_provider_id)
            if provider:
                logger.debug(f"Using auth provider from config: {config_provider_id}")
                return provider
            else:
                logger.warning(f"Auth provider from config not found: {config_provider_id}")

        # Auth provider not found
        return None

    def _process_advanced_params(
        self,
        config: Dict[str, Any],
        lifespan: Optional[Callable[[Any], Any]] = None,
        tags: Optional[Set[str]] = None,
        dependencies: Optional[List[str]] = None,
        tool_serializer: Optional[Callable[[Any], str]] = None,
    ) -> Dict[str, Any]:
        """Process advanced parameters.

        Args:
            config: Configuration dictionary
            lifespan: Server lifecycle manager
            tags: Server tag set
            dependencies: Server dependencies list
            tool_serializer: Tool result serializer

        Returns:
            Processed advanced parameters dictionary
        """
        result = {}

        # Process server constructor parameters
        if lifespan:
            result["lifespan"] = lifespan

        if tool_serializer:
            result["tool_serializer"] = tool_serializer

        # Extract and merge tags and dependencies from advanced configuration
        advanced_config = param_utils.extract_config_section(config, "advanced")

        # Process tags (merge API parameters and configuration)
        config_tags = advanced_config.get("tags", [])
        if config_tags:
            config_tags = set(config_tags)

        merged_tags = param_utils.merge_tags(tags, config_tags)
        if merged_tags:
            result["tags"] = merged_tags

        # Process dependencies (merge API parameters and configuration)
        config_deps = advanced_config.get("dependencies", [])
        merged_deps = param_utils.merge_dependencies(dependencies, config_deps)
        if merged_deps:
            result["dependencies"] = merged_deps

        return result
