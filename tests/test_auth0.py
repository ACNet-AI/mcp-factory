"""Unit test module for Auth0Provider authentication provider."""

from unittest.mock import MagicMock, patch

import pytest

from fastmcp_factory.auth.auth0 import Auth0Provider


# Test Auth0Provider initialization
def test_auth0_provider_init() -> None:
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

    # Test default audience value when not provided
    provider_default_audience = Auth0Provider(
        domain="example.auth0.com",
        client_id="client_id_example",
        client_secret="client_secret_example",
    )
    assert provider_default_audience.audience == "https://example.auth0.com/api/v2/"


# Test get_token method with code exchange flow
@pytest.mark.asyncio
async def test_get_token() -> None:
    """Test get_token method with code exchange flow."""
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

        # Verify result
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


# Test get_userinfo method with token
@pytest.mark.asyncio
async def test_get_userinfo() -> None:
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
        "https://your-domain.com/roles": ["user", "admin"],
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value=mock_userinfo)

    # Patch httpx.AsyncClient.get method
    with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
        # Call the method being tested
        userinfo = await provider.get_userinfo("test_token")

        # Verify result
        assert userinfo["sub"] == "user123"
        assert userinfo["name"] == "Test User"

        # Verify call parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "https://example.auth0.com/userinfo"
        assert kwargs["headers"]["Authorization"] == "Bearer test_token"


# Test token validation method
@pytest.mark.asyncio
async def test_validate_token() -> None:
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


# Test get_user_for_token method with valid and invalid tokens
@pytest.mark.asyncio
async def test_get_user_for_token() -> None:
    """Test get_user_for_token method with valid and invalid tokens."""
    # Create Auth0Provider instance
    provider = Auth0Provider(
        domain="example.auth0.com",
        client_id="client_id_example",
        client_secret="client_secret_example",
    )

    # Test user info with roles
    mock_userinfo = {
        "sub": "user123",
        "name": "Test User",
        "email": "test@example.com",
        "https://your-domain.com/roles": ["user", "admin"],
    }

    with patch.object(provider, "get_userinfo", return_value=mock_userinfo) as mock_get_userinfo:
        # Get user info
        user = await provider.get_user_for_token("test_token")

        # Verify result
        assert user["id"] == "user123"
        assert user["name"] == "Test User"
        assert user["email"] == "test@example.com"
        assert "admin" in user["roles"]
        assert user["is_admin"] is True
        assert user["raw"] == mock_userinfo

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

        # Verify result
        assert user["id"] == "user456"
        assert user["name"] == "Regular User"
        assert user["roles"] == []
        assert user["is_admin"] is False

        # Verify call
        mock_get_userinfo.assert_called_once_with("test_token")

    # Test exception case
    with patch.object(
        provider, "get_userinfo", side_effect=Exception("API Error")
    ) as mock_get_userinfo:
        # Get user info
        user = await provider.get_user_for_token("test_token")

        # Verify result
        assert "error" in user
        assert "API Error" in user["error"]
        assert user["roles"] == []
        assert user["is_admin"] is False

        # Verify call
        mock_get_userinfo.assert_called_once_with("test_token")
