"""Unit test module for authentication-related components."""

from unittest.mock import MagicMock, patch

import pytest

from fastmcp_factory.auth.auth0 import Auth0Provider


class TestAuth0Provider:
    """Test Auth0Provider authentication provider."""

    def test_provider_initialization(self) -> None:
        """Test Auth0Provider initialization parameter settings."""
        provider = Auth0Provider(
            domain="example.auth0.com",
            client_id="client_id_example",
            client_secret="client_secret_example",
            audience="https://example.auth0.com/api/v2/",
        )

        # Verify initialization parameters
        assert provider.domain == "example.auth0.com"
        assert provider.client_id == "client_id_example"
        assert provider.client_secret == "client_secret_example"
        assert provider.audience == "https://example.auth0.com/api/v2/"
        assert provider.token_url == "https://example.auth0.com/oauth/token"
        assert provider.userinfo_url == "https://example.auth0.com/userinfo"

        # Test default audience value (when not provided)
        provider_default_audience = Auth0Provider(
            domain="example.auth0.com",
            client_id="client_id_example",
            client_secret="client_secret_example",
        )
        assert provider_default_audience.audience == "https://example.auth0.com/api/v2/"

    @pytest.mark.asyncio
    async def test_get_token(self) -> None:
        """Test get_token method with authorization code exchange flow."""
        # Create Auth0Provider instance
        provider = Auth0Provider(
            domain="example.auth0.com",
            client_id="client_id_example",
            client_secret="client_secret_example",
        )

        # Mock POST response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "access_token": "mock_access_token",
                "token_type": "Bearer",
                "expires_in": 86400,
            }
        )

        # Patch httpx.AsyncClient.post method
        with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
            # Call the method being tested
            result = await provider.get_token("auth_code", "https://example.com/callback")

            # Verify results
            assert result["access_token"] == "mock_access_token"
            assert result["token_type"] == "Bearer"

            # Verify call parameters
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://example.auth0.com/oauth/token"
            assert kwargs["data"]["grant_type"] == "authorization_code"
            assert kwargs["data"]["code"] == "auth_code"
            assert kwargs["data"]["client_id"] == "client_id_example"
            assert kwargs["data"]["client_secret"] == "client_secret_example"

    @pytest.mark.asyncio
    async def test_get_userinfo(self) -> None:
        """Test get_userinfo method with token."""
        # Create Auth0Provider instance
        provider = Auth0Provider(
            domain="example.auth0.com",
            client_id="client_id_example",
            client_secret="client_secret_example",
        )

        # Mock GET response
        mock_userinfo = {
            "sub": "user123",
            "name": "Test User",
            "email": "test@example.com",
            "https://example.auth0.com/roles": ["user", "admin"],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=mock_userinfo)

        # Patch httpx.AsyncClient.get method
        with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
            # Call the method being tested
            userinfo = await provider.get_userinfo("test_token")

            # Verify results
            assert userinfo["sub"] == "user123"
            assert userinfo["name"] == "Test User"

            # Verify call parameters
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert args[0] == "https://example.auth0.com/userinfo"
            assert kwargs["headers"]["Authorization"] == "Bearer test_token"

    @pytest.mark.asyncio
    async def test_validate_token(self) -> None:
        """Test token validation method."""
        # Create Auth0Provider instance
        provider = Auth0Provider(
            domain="example.auth0.com",
            client_id="client_id_example",
            client_secret="client_secret_example",
        )

        # Test valid token
        with patch.object(
            provider, "get_userinfo", return_value={"sub": "user123"}
        ) as mock_get_userinfo:
            # Verify valid token returns True
            assert await provider.validate_token("valid_token") is True
            mock_get_userinfo.assert_called_once_with("valid_token")

        # Test invalid token
        with patch.object(
            provider, "get_userinfo", side_effect=Exception("Invalid token")
        ) as mock_get_userinfo:
            # Verify invalid token returns False
            assert await provider.validate_token("invalid_token") is False
            mock_get_userinfo.assert_called_once_with("invalid_token")

    @pytest.mark.asyncio
    async def test_get_user_roles(self) -> None:
        """Test method for getting user roles."""
        # Create Auth0Provider instance
        provider = Auth0Provider(
            domain="example.auth0.com",
            client_id="client_id_example",
            client_secret="client_secret_example",
        )

        # Set roles namespace
        provider.roles_namespace = "https://example.auth0.com/roles"

        # Test user info with roles
        mock_userinfo = {
            "sub": "user123",
            "name": "Test User",
            "email": "test@example.com",
            "https://example.auth0.com/roles": ["user", "admin"],
        }

        with patch.object(
            provider, "get_userinfo", return_value=mock_userinfo
        ) as mock_get_userinfo:
            # Get user info using get_user_for_token method
            user_info = await provider.get_user_for_token("test_token")

            # Get roles
            roles = user_info["roles"]

            # Verify results
            assert "user" in roles
            assert "admin" in roles
            assert len(roles) == 2

            # Verify call
            mock_get_userinfo.assert_called_once_with("test_token")

        # Test user info without roles
        mock_userinfo_no_roles = {
            "sub": "user456",
            "name": "Regular User",
            "email": "normal@example.com",
        }

        with patch.object(
            provider, "get_userinfo", return_value=mock_userinfo_no_roles
        ) as mock_get_userinfo:
            # Get user info
            user_info = await provider.get_user_for_token("test_token")

            # Get roles
            roles = user_info["roles"]

            # Verify results
            assert roles == []

            # Verify call
            mock_get_userinfo.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_get_user_for_token(self) -> None:
        """Test method for getting user information from token."""
        # Create Auth0Provider instance
        provider = Auth0Provider(
            domain="example.auth0.com",
            client_id="client_id_example",
            client_secret="client_secret_example",
        )

        # Set roles namespace
        provider.roles_namespace = "https://example.auth0.com/roles"

        # Test user info with roles
        mock_userinfo = {
            "sub": "user123",
            "name": "Test User",
            "email": "test@example.com",
            "https://example.auth0.com/roles": ["user", "admin"],
        }

        with patch.object(
            provider, "get_userinfo", return_value=mock_userinfo
        ) as mock_get_userinfo:
            # Get user info
            user = await provider.get_user_for_token("test_token")

            # Verify results
            assert user["id"] == "user123"
            assert user["name"] == "Test User"
            assert user["email"] == "test@example.com"
            assert "admin" in user["roles"]

            # Verify call
            mock_get_userinfo.assert_called_once_with("test_token")

        # Test user info without roles
        mock_userinfo_no_roles = {
            "sub": "user456",
            "name": "Regular User",
            "email": "normal@example.com",
        }

        with patch.object(
            provider, "get_userinfo", return_value=mock_userinfo_no_roles
        ) as mock_get_userinfo:
            # Get user info
            user = await provider.get_user_for_token("test_token")

            # Verify results
            assert user["id"] == "user456"
            assert user["name"] == "Regular User"
            assert user["roles"] == []

            # Verify call
            mock_get_userinfo.assert_called_once_with("test_token")

        # Test exception handling
        with patch.object(
            provider, "get_userinfo", side_effect=Exception("API Error")
        ) as mock_get_userinfo:
            # Get user info
            user = await provider.get_user_for_token("test_token")

            # Verify results
            assert "error" in user
            assert "API Error" in user["error"]
            assert user["roles"] == []

            # Verify call
            mock_get_userinfo.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_get_user_roles_from_app_metadata(self) -> None:
        """Test getting user roles from app_metadata."""
        # Create Auth0Provider instance
        provider = Auth0Provider(
            domain="example.auth0.com",
            client_id="client_id_example",
            client_secret="client_secret_example",
        )

        # Set roles namespace, but user info does not include it
        provider.roles_namespace = "https://example.auth0.com/roles"

        # User info includes app_metadata field and roles
        mock_userinfo = {
            "sub": "user789",
            "name": "Metadata User",
            "email": "metadata@example.com",
            "app_metadata": {"roles": ["developer", "tester"], "other_data": "some value"},
        }

        with patch.object(
            provider, "get_userinfo", return_value=mock_userinfo
        ) as mock_get_userinfo:
            # Get user info
            user_info = await provider.get_user_for_token("test_token")

            # Verify results
            assert "developer" in user_info["roles"]
            assert "tester" in user_info["roles"]
            assert len(user_info["roles"]) == 2
            assert user_info["is_admin"] is False  # No admin role

            # Verify call
            mock_get_userinfo.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_get_user_roles_from_permissions(self) -> None:
        """Test getting user roles from permissions."""
        # Create Auth0Provider instance
        provider = Auth0Provider(
            domain="example.auth0.com",
            client_id="client_id_example",
            client_secret="client_secret_example",
        )

        # Set roles namespace, but user info does not include it or app_metadata
        provider.roles_namespace = "https://example.auth0.com/roles"

        # User info includes permissions field
        mock_userinfo = {
            "sub": "user789",
            "name": "Permissions User",
            "email": "permissions@example.com",
            "permissions": ["read:data", "write:data", "admin"],
        }

        with patch.object(
            provider, "get_userinfo", return_value=mock_userinfo
        ) as mock_get_userinfo:
            # Get user info
            user_info = await provider.get_user_for_token("test_token")

            # Verify results
            assert "read:data" in user_info["roles"]
            assert "write:data" in user_info["roles"]
            assert "admin" in user_info["roles"]
            assert len(user_info["roles"]) == 3
            assert user_info["is_admin"] is True  # Includes admin role

            # Verify call
            mock_get_userinfo.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_get_user_for_token_exception_handling(self) -> None:
        """Test handling exceptions when getting user information."""
        # Create Auth0Provider instance
        provider = Auth0Provider(
            domain="example.auth0.com",
            client_id="client_id_example",
            client_secret="client_secret_example",
        )

        # Mock get_userinfo method to raise exception
        with patch.object(
            provider, "get_userinfo", side_effect=Exception("API error")
        ) as mock_get_userinfo:
            # Get user info
            user_info = await provider.get_user_for_token("invalid_token")

            # Verify results
            assert "error" in user_info
            assert "API error" in user_info["error"]
            assert user_info["roles"] == []
            assert user_info["is_admin"] is False

            # Verify call
            mock_get_userinfo.assert_called_once_with("invalid_token")


class TestAuthRegistry:
    """Test authentication provider registry."""

    def test_provider_management(self) -> None:
        """Test authentication provider registry provider management functionality."""
        from fastmcp_factory.auth.registry import AuthProviderRegistry

        # Create registry
        registry = AuthProviderRegistry()

        # Create mock provider
        mock_provider = MagicMock()
        mock_provider.domain = "example.auth0.com"

        # Test adding provider
        if hasattr(registry, "add_provider"):
            registry.add_provider("test-provider", mock_provider)
        elif hasattr(registry, "create_provider"):
            # If using factory method to create provider
            with patch.object(registry, "create_provider", return_value=mock_provider):
                registry._providers = {"test-provider": mock_provider}

        # Test getting provider
        assert registry.get_provider("test-provider") is mock_provider
        assert registry.get_provider("non-existent") is None

    def test_create_provider(self) -> None:
        """Test method for creating authentication provider."""
        from fastmcp_factory.auth.registry import AuthProviderRegistry

        # Create registry
        registry = AuthProviderRegistry()

        # Mock Auth0Provider class
        mock_auth0_provider = MagicMock()

        # Test creating Auth0 provider
        with patch(
            "fastmcp_factory.auth.auth0.Auth0Provider", return_value=mock_auth0_provider
        ) as mock_provider_class:
            # Create provider
            provider_config = {
                "domain": "test.auth0.com",
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "audience": "test-audience",
                "roles_namespace": "test-namespace",
            }

            provider = registry.create_provider(
                provider_id="test-auth0", provider_type="auth0", config=provider_config
            )

            # Verify provider created successfully
            assert provider is mock_auth0_provider

            # Verify call parameters
            mock_provider_class.assert_called_once_with(
                domain="test.auth0.com",
                client_id="test-client-id",
                client_secret="test-client-secret",
                audience="test-audience",
                roles_namespace="test-namespace",
            )

            # Verify provider added to registry
            assert registry.get_provider("test-auth0") is mock_auth0_provider

    def test_create_provider_missing_params(self) -> None:
        """Test creating provider when missing necessary parameters."""
        from fastmcp_factory.auth.registry import AuthProviderRegistry

        # Create registry
        registry = AuthProviderRegistry()

        # Config with missing necessary parameters
        incomplete_config = {
            "domain": "test.auth0.com",
            # Missing client_id and client_secret
        }

        # Test creating provider
        provider = registry.create_provider(
            provider_id="test-auth0", provider_type="auth0", config=incomplete_config
        )

        # Verify provider created failed
        assert provider is None

    def test_create_provider_unsupported_type(self) -> None:
        """Test creating unsupported type provider."""
        from fastmcp_factory.auth.registry import AuthProviderRegistry

        # Create registry
        registry = AuthProviderRegistry()

        # Test creating unsupported provider type
        provider = registry.create_provider(
            provider_id="test-unsupported", provider_type="unsupported", config={}
        )

        # Verify provider created failed
        assert provider is None

    def test_list_providers(self) -> None:
        """Test listing all providers."""
        from fastmcp_factory.auth.registry import AuthProviderRegistry

        # Create registry
        registry = AuthProviderRegistry()

        # Add mock providers
        mock_provider1 = MagicMock()
        mock_provider1.__class__.__name__ = "Auth0Provider"

        mock_provider2 = MagicMock()
        mock_provider2.__class__.__name__ = "OAuthProvider"

        registry._providers = {"provider1": mock_provider1, "provider2": mock_provider2}

        # Get provider list
        providers = registry.list_providers()

        # Verify results
        assert providers == {"provider1": "Auth0Provider", "provider2": "OAuthProvider"}

    def test_remove_provider(self) -> None:
        """Test removing provider."""
        from fastmcp_factory.auth.registry import AuthProviderRegistry

        # Create registry
        registry = AuthProviderRegistry()

        # Add mock provider
        mock_provider = MagicMock()
        registry._providers = {"test-provider": mock_provider}

        # Remove provider
        result = registry.remove_provider("test-provider")

        # Verify results
        assert result is True
        assert "test-provider" not in registry._providers

        # Test removing non-existent provider
        result = registry.remove_provider("non-existent")

        # Verify results
        assert result is False
