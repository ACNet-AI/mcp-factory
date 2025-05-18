"""FastMCP-Factory test configuration and shared fixture."""

import asyncio
import tracemalloc
from typing import Any
from unittest.mock import MagicMock

import pytest

from fastmcp_factory import FastMCPFactory
from fastmcp_factory.server import ManagedServer


# Set up asynchronous pytest session
def pytest_configure(config: Any) -> None:
    """Configure pytest."""
    # Ensure asyncio warnings are handled
    asyncio.get_event_loop_policy().new_event_loop()
    # Enable tracemalloc for memory allocation tracking
    tracemalloc.start()


# Note: Do not redefine event loop fixture, let pytest-asyncio use its own implementation
# Should be controlled by setting asyncio_default_fixture_loop_scope in pyproject.toml


@pytest.fixture
def mock_auth_provider() -> MagicMock:
    """Create a mock Auth0Provider."""
    mock_provider = MagicMock()
    # Mock get_user_for_token method to return a user with admin role
    mock_provider.get_user_for_token.return_value = {
        "id": "test-user",
        "name": "Test User",
        "email": "test@example.com",
        "roles": ["admin"],
        "is_admin": True,
    }
    return mock_provider


@pytest.fixture
def factory(mock_auth_provider: MagicMock) -> FastMCPFactory:
    """Create a FastMCPFactory instance."""
    return FastMCPFactory(auth_server_provider=mock_auth_provider)


@pytest.fixture
def basic_server() -> ManagedServer:
    """Create a basic ManagedServer instance."""
    return ManagedServer(name="test-server", instructions="Test server", auto_register=False)


@pytest.fixture
def auto_register_server(mock_auth_provider: MagicMock) -> ManagedServer:
    """Create a ManagedServer instance with auto-registration enabled."""
    return ManagedServer(
        name="auto-test-server",
        instructions="Auto-registration test server",
        auto_register=True,
        auth_server_provider=mock_auth_provider,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )


@pytest.fixture
def factory_server(factory: FastMCPFactory) -> ManagedServer:
    """Create a server via factory."""
    return factory.create_managed_server(
        name="factory-server",
        instructions="Factory created server",
        auto_register=True,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )
