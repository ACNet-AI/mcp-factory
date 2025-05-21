"""FastMCP-Factory test configuration and shared fixtures."""

import asyncio
import os
import shutil
import tempfile
import tracemalloc
from typing import Any, Generator
from unittest.mock import MagicMock

import pytest
import yaml

from mcp_factory import FastMCPFactory
from mcp_factory.server import ManagedServer


# Set up asynchronous pytest session
def pytest_configure(config: Any) -> None:
    """Configure pytest session."""
    # Ensure asyncio warnings are handled
    asyncio.get_event_loop_policy().new_event_loop()
    # Enable tracemalloc for memory allocation tracking
    tracemalloc.start()

    # Add filter to ignore expected authentication provider warnings
    config.addinivalue_line(
        "filterwarnings",
        "ignore:Exposing FastMCP native methods as management tools without "
        "authentication.*:UserWarning",
    )


# Provide mock authentication provider object
@pytest.fixture
def mock_auth_provider() -> MagicMock:
    """Return a mock authentication provider object."""
    provider = MagicMock()
    provider.domain = "example.auth0.com"
    provider.client_id = "test_client_id"
    provider.client_secret = "test_client_secret"
    provider.validate_token = MagicMock(return_value=True)
    provider.get_user_for_token = MagicMock(return_value={"id": "test-user", "roles": ["user"]})
    return provider


# Provide temporary configuration file
@pytest.fixture
def temp_config_file() -> Generator[str, None, None]:
    """Create a temporary test configuration file and clean up after the test."""
    # Create temporary configuration file
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
        config = {
            "server": {
                "name": "test-server",
                "instructions": "Test server configuration",
                "host": "localhost",
                "port": 8080,
            }
        }
        yaml_content = yaml.dump(config)
        temp_file.write(yaml_content.encode("utf-8"))
        config_path = temp_file.name

    # Provide file path
    yield config_path

    # Clean up temporary file
    if os.path.exists(config_path):
        os.unlink(config_path)


# Create temporary directory for testing
@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for testing, automatically cleaned up after the test."""
    # Create temporary directory
    temp_dir_path = tempfile.mkdtemp()

    # Provide directory path
    yield temp_dir_path

    # Clean up directory after test
    shutil.rmtree(temp_dir_path, ignore_errors=True)


# Provide configured FastMCPFactory instance
@pytest.fixture
def factory() -> FastMCPFactory:
    """Return a configured FastMCPFactory instance."""
    return FastMCPFactory()


# Provide configured ManagedServer instance
@pytest.fixture
def server() -> ManagedServer:
    """Return a basic configured ManagedServer instance."""
    return ManagedServer(name="test-server", instructions="Test server for pytest")


# Provide ManagedServer instance with authentication
@pytest.fixture
def auth_server(mock_auth_provider: MagicMock) -> ManagedServer:
    """Return a ManagedServer instance configured with authentication."""
    return ManagedServer(
        name="auth-test-server",
        instructions="Test authentication configuration",
        auth_server_provider=mock_auth_provider,
        auth={"issuer_url": "https://example.auth0.com", "token_endpoint": "/oauth/token"},
    )
