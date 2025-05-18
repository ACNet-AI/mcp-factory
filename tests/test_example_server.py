"""Example server tests for functional verification."""

from unittest.mock import MagicMock, patch

import pytest

from fastmcp_factory import FastMCPFactory
from fastmcp_factory.auth.auth0 import Auth0Provider


@pytest.mark.asyncio
async def test_example_server_setup() -> None:
    """Test basic example server setup and configuration."""
    # Mock Auth0 provider
    mock_auth = MagicMock(spec=Auth0Provider)

    # Create factory
    factory = FastMCPFactory(auth_server_provider=mock_auth)

    # Create server
    server = factory.create_managed_server(
        name="example-server",
        instructions="This is an example server providing basic tool functionality",
        tags={"demo", "example"},
        dependencies=["fastmcp-factory"],
        auto_register=True,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )

    # Add custom tool
    @server.tool(name="greet", description="Greet the specified user")
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    # Verify custom tool is registered
    tools = await server.get_tools()
    assert "greet" in tools

    # Verify management tools are registered
    management_tools = [t for t in tools if t.startswith("manage_")]
    assert len(management_tools) > 0

    # Verify server name and instructions
    assert server.name == "example-server"
    assert "providing basic tool functionality" in server.instructions


@pytest.mark.asyncio
async def test_multiple_servers() -> None:
    """Test factory managing multiple servers with different configurations."""
    # Create factory instance
    mock_auth = MagicMock(spec=Auth0Provider)
    factory = FastMCPFactory(auth_server_provider=mock_auth)

    # Create first server (auto-register)
    server1 = factory.create_managed_server(
        name="server1",
        instructions="Server 1",
        auto_register=True,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )

    # Create second server (no auto-register)
    server2 = factory.create_managed_server(
        name="server2",
        instructions="Server 2",
        auto_register=False,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )

    # Add tools to second server
    @server2.tool(name="say_goodbye", description="Say goodbye to the user")
    def say_goodbye(name: str) -> str:
        return f"Goodbye, {name}!"

    # Verify factory has two servers
    servers = factory.list_servers()
    assert "server1" in servers
    assert "server2" in servers

    # Verify first server has management tools
    tools1 = await server1.get_tools()
    management_tools = [t for t in tools1 if t.startswith("manage_")]
    assert len(management_tools) > 0

    # Verify second server has no management tools, but has custom tools
    tools2 = await server2.get_tools()
    management_tools2 = [t for t in tools2 if t.startswith("manage_")]
    assert len(management_tools2) == 0
    assert "say_goodbye" in tools2

    # Test server removal
    factory.remove_server("server2")
    remaining_servers = factory.list_servers()
    assert "server1" in remaining_servers
    assert "server2" not in remaining_servers


@pytest.mark.asyncio
async def test_auth_integration() -> None:
    """Test Auth0 integration with managed server."""
    # Create mock Auth0 provider
    with patch("fastmcp_factory.auth.auth0.Auth0Provider") as mock_auth_class:
        mock_auth = mock_auth_class.return_value

        # Set up mock behavior
        mock_auth.get_user_roles.return_value = ["admin"]

        # Create factory
        factory = FastMCPFactory(auth_server_provider=mock_auth)

        # Create server
        server = factory.create_managed_server(
            name="auth-test-server",
            instructions="Authentication test server",
            auto_register=True,
            auth={
                "issuer_url": "https://example.auth0.com",
            },
        )

        # Verify server creation successful
        assert server.name == "auth-test-server"

        # Verify management tools are registered
        tools = await server.get_tools()
        management_tools = [t for t in tools if t.startswith("manage_")]
        assert len(management_tools) > 0
