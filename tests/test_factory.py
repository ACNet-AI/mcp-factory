"""Unit test module for the FastMCPFactory class."""

import inspect
import os
from unittest.mock import MagicMock

from fastmcp_factory import FastMCPFactory


# Basic tests
def test_factory_basics() -> None:
    """Test basic factory initialization and properties."""
    # Initialize factory
    factory = FastMCPFactory()

    # Verify initial state
    assert factory.servers == {}
    assert factory.auth_server_provider is None
    assert factory.factory_config == {}

    # Verify factory methods
    assert factory.list_servers() == []
    assert factory.get_server("non-existent") is None


# Test factory creation with configuration
def test_factory_with_config() -> None:
    """Test factory creation with custom configuration."""
    # Create factory with configuration
    factory = FastMCPFactory(auth_server_provider=MagicMock(), custom_setting="test_value")

    # Verify configuration
    assert factory.auth_server_provider is not None
    assert factory.factory_config == {"custom_setting": "test_value"}


# Test server creation
def test_create_server() -> None:
    """Test server creation through factory."""
    mock_auth = MagicMock()
    factory = FastMCPFactory(auth_server_provider=mock_auth)

    # Provide name parameter directly
    server1 = factory.create_managed_server(
        name="test-server",
        instructions="Test server",
        auth_server_provider=mock_auth,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )

    # Pass name parameter through server_kwargs (tests line 44)
    server2 = factory.create_managed_server(
        instructions="Test server 2",
        name="test-server2",  # will be extracted
        auth_server_provider=mock_auth,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )

    # Verify servers are added to the factory
    assert "test-server" in factory.servers
    assert "test-server2" in factory.servers
    assert factory.get_server("test-server") is server1
    assert factory.get_server("test-server2") is server2


# Test unnamed server scenario
def test_create_unnamed_server() -> None:
    """Test creating an unnamed server (covers line 69)."""
    mock_auth_provider = MagicMock()
    factory = FastMCPFactory()

    # Create unnamed server
    # Unnamed servers should not be saved in the factory, no need to save return value
    factory.create_managed_server(
        instructions="Unnamed server",
        auth_server_provider=mock_auth_provider,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )

    # Verify server is not added to the factory's server list
    assert len(factory.servers) == 0
    assert factory.list_servers() == []


# Test server removal
def test_remove_server() -> None:
    """Test server removal functionality (covers line 90)."""
    mock_auth_provider = MagicMock()
    factory = FastMCPFactory()

    # Create two servers
    factory.create_managed_server(
        name="server1",
        instructions="Server 1",
        auth_server_provider=mock_auth_provider,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )

    factory.create_managed_server(
        name="server2",
        instructions="Server 2",
        auth_server_provider=mock_auth_provider,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )

    # Verify server list
    assert "server1" in factory.list_servers()
    assert "server2" in factory.list_servers()

    # Test removing an existing server
    result = factory.remove_server("server1")
    assert result is True
    assert "server1" not in factory.list_servers()
    assert "server2" in factory.list_servers()

    # Test removing a non-existent server (covers line 90)
    result = factory.remove_server("non-existent")
    assert result is False
    assert factory.list_servers() == ["server2"]


def test_factory_code_inspection() -> None:
    """Verify expected logic in factory.py through code inspection."""
    # Get source code for FastMCPFactory.create_managed_server
    source_code = inspect.getsource(FastMCPFactory.create_managed_server)

    # Check if source code contains expected conditional statement
    expected_code = "if name is None and 'name' in server_kwargs:"
    assert expected_code in source_code, "Expected conditional statement not found in factory.py"

    # Get the code line after the conditional statement, should be an assignment
    assignment_line = "name = server_kwargs.pop('name')"
    assert assignment_line in source_code, "Expected assignment statement not found in factory.py"

    # By reading the factory class file, ensure code contains expected content
    factory_file = os.path.abspath(inspect.getfile(FastMCPFactory))
    with open(factory_file) as f:
        content = f.read()
        # Verify file contains expected code
        assert expected_code in content, (
            "Expected conditional statement not found in FastMCPFactory file"
        )
        assert assignment_line in content, (
            "Expected assignment statement not found in FastMCPFactory file"
        )
