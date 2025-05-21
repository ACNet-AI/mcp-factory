"""Authentication Provider Registry Module.

This module provides the AuthProviderRegistry class for creating and managing
authentication provider instances.
"""

import logging
from typing import Any, Dict, Optional

from mcp.server.auth.provider import OAuthAuthorizationServerProvider

# Set up logging
logger = logging.getLogger(__name__)


class AuthProviderRegistry:
    """Authentication provider registry.
    
    This class is responsible for creating and managing different types of
    authentication providers. It provides methods to create, get, list, and remove
    authentication providers.
    """

    #######################
    # Initialization
    #######################

    def __init__(self) -> None:
        """Initialize authentication provider registry."""
        self._providers: Dict[str, OAuthAuthorizationServerProvider] = {}

    #######################
    # Provider Management Methods
    #######################

    def create_provider(
        self, provider_id: str, provider_type: str, config: Dict[str, Any]
    ) -> Optional[OAuthAuthorizationServerProvider]:
        """Create and register an authentication provider.

        Args:
            provider_id: Unique identifier for the provider
            provider_type: Provider type ("auth0", "oauth", etc.)
            config: Provider configuration parameters

        Returns:
            Created authentication provider, or None if creation failed

        Raises:
            ValueError: If provider_type is not supported
        """
        if provider_id in self._providers:
            logger.warning(f"Provider '{provider_id}' already exists and will be replaced")

        try:
            if provider_type.lower() == "auth0":
                # Import on demand to avoid circular dependencies
                from fastmcp_factory.auth.auth0 import Auth0Provider

                required_params = ["domain", "client_id", "client_secret"]
                if not all(param in config for param in required_params):
                    missing = [p for p in required_params if p not in config]
                    raise ValueError(f"Missing required parameters: {', '.join(missing)}")

                provider = Auth0Provider(
                    domain=config["domain"],
                    client_id=config["client_id"],
                    client_secret=config["client_secret"],
                    audience=config.get("audience"),
                    roles_namespace=config.get("roles_namespace"),
                )

                self._providers[provider_id] = provider
                logger.info(
                    f"Authentication provider created successfully: {provider_id} "
                    f"(type: {provider_type})"
                )
                return provider
            else:
                raise ValueError(f"Unsupported provider type: {provider_type}")
        except Exception as e:
            logger.error(f"Failed to create authentication provider '{provider_id}': {str(e)}")
            return None

    def get_provider(self, provider_id: str) -> Optional[OAuthAuthorizationServerProvider]:
        """Get authentication provider by ID.

        Args:
            provider_id: Provider identifier

        Returns:
            Authentication provider instance, or None if it doesn't exist
        """
        return self._providers.get(provider_id)

    def list_providers(self) -> Dict[str, str]:
        """List all registered authentication providers.

        Returns:
            Dictionary mapping provider IDs to their types
        """
        return {
            provider_id: provider.__class__.__name__
            for provider_id, provider in self._providers.items()
        }

    def remove_provider(self, provider_id: str) -> bool:
        """Remove an authentication provider.

        Args:
            provider_id: Provider identifier

        Returns:
            Whether removal was successful
        """
        if provider_id in self._providers:
            del self._providers[provider_id]
            logger.info(f"Authentication provider removed: {provider_id}")
            return True
        return False
