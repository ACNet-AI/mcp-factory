"""Unit test module for the ManagedServer class."""

import inspect
import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from fastmcp_factory import FastMCPFactory
from fastmcp_factory.server import ManagedServer


# Basic functionality tests
def test_managed_server_init() -> None:
    """Test ManagedServer basic initialization functionality."""
    # Create a server without auto-registration
    server = ManagedServer(name="test-server", instructions="Test server", auto_register=False)

    assert server.name == "test-server"
    assert server.instructions == "Test server"


# Auto-registration functionality tests
@pytest.mark.asyncio
async def test_auto_register_tools(mock_auth_provider: Any) -> None:
    """Test automatic registration of FastMCP methods as tools."""
    # Create a server with auto-registration enabled
    server = ManagedServer(
        name="test-server",
        instructions="Test server",
        auto_register=True,
        auth_server_provider=mock_auth_provider,
    )

    # Get the tool list
    tools = await server.get_tools()

    # Verify management tools are registered
    management_tools = [t for t in tools if t.startswith("manage_")]
    assert len(management_tools) > 0

    # Check for common management tools
    assert "manage_tool" in management_tools
    assert "manage_reload_config" in management_tools


# Test warnings
def test_warning_without_auth() -> None:
    """Test warning when authentication mechanism is not configured."""
    with pytest.warns(UserWarning, match="authentication mechanism not configured"):
        ManagedServer(name="test-server", instructions="Test server", auto_register=True)


# Test EXCLUDED_METHODS functionality
@pytest.mark.asyncio
async def test_excluded_methods(mock_auth_provider: Any) -> None:
    """Test excluded methods are not registered as tools."""
    server = ManagedServer(
        name="test-server",
        instructions="Test server",
        auto_register=True,
        auth_server_provider=mock_auth_provider,
    )

    tools = await server.get_tools()

    # Check that excluded methods are not registered
    for method in ManagedServer.EXCLUDED_METHODS:
        if not method.startswith("__"):  # Skip special methods
            assert f"manage_{method}" not in tools


# Test server with authentication mechanism
@pytest.mark.asyncio
async def test_with_auth_provider() -> None:
    """Test server with authentication mechanism does not produce warnings."""
    # Mock an authentication provider
    mock_auth = MagicMock()

    # Use patch to directly capture warnings from auto_register module
    with patch("fastmcp_factory.server.warnings") as mock_warnings:
        server = ManagedServer(
            name="test-server",
            instructions="Test server",
            auto_register=True,
            auth_server_provider=mock_auth,
            auth={
                "issuer_url": "https://example.auth0.com",
            },
        )

        # Verify that the warning about no authentication mechanism is not triggered
        for call in mock_warnings.warn.call_args_list:
            args, _ = call
            # Ensure that the specific warning about no authentication mechanism is not triggered
            warning_message = str(args[0]) if args else ""
            assert "authentication mechanism not configured" not in warning_message

        # Get tools and verify management tools are registered
        tools = await server.get_tools()
        management_tools = [t for t in tools if t.startswith("manage_")]
        assert len(management_tools) > 0


# Test factory integration
@pytest.mark.asyncio
async def test_factory_integration() -> None:
    """Test FastMCPFactory integration with ManagedServer."""
    # Create factory instance with authentication provider
    mock_auth = MagicMock()
    factory = FastMCPFactory(auth_server_provider=mock_auth)

    # Create server
    server = factory.create_managed_server(
        name="factory-test-server",
        instructions="Factory-created test server",
        auto_register=True,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )

    # Verify server has been added to factory
    assert "factory-test-server" in factory.list_servers()

    # Verify server type
    assert isinstance(server, ManagedServer)

    # Verify management tools are registered
    tools = await server.get_tools()
    management_tools = [t for t in tools if t.startswith("manage_")]
    assert len(management_tools) > 0


# Test authentication configuration in run method
def test_run_with_auth_config(mock_auth_provider: Any) -> None:
    """Test passing authentication configuration at runtime (covers lines 101-113 in server.py)."""
    # Set up a mock server with authentication configuration
    server = ManagedServer(
        name="auth-test-server",
        instructions="Test authentication configuration",
        auto_register=False,
        auth_server_provider=mock_auth_provider,
        auth={"issuer_url": "https://example.auth0.com", "token_endpoint": "/oauth/token"},
        # Add some runtime parameters
        host="localhost",
        port=8080,
    )

    # Mock FastMCP's run method
    with patch("fastmcp.FastMCP.run") as mock_run:
        # Call server's run method
        server.run(transport="streamable-http", debug=True)

        # Validate call parameters
        call_args = mock_run.call_args[1]

        # Check if authentication configuration is correctly passed
        assert call_args["transport"] == "streamable-http"
        assert call_args["debug"]  # Use Python's native boolean check
        assert call_args["host"] == "localhost"
        assert call_args["port"] == 8080
        assert call_args["auth_server_provider"] == mock_auth_provider
        assert "auth" in call_args
        assert call_args["auth"]["issuer_url"] == "https://example.auth0.com"
        assert call_args["auth"]["token_endpoint"] == "/oauth/token"

    # Test call without transport parameter
    with patch("fastmcp.FastMCP.run") as mock_run:
        server.run(debug=True)

        # Validate call parameters
        call_args = mock_run.call_args[1]

        # Check if authentication configuration is correctly passed
        assert "transport" not in call_args
        assert call_args["debug"]  # Use Python's native boolean check
        assert call_args["auth_server_provider"] == mock_auth_provider
        assert "auth" in call_args


# Test registration of reload_config method
@pytest.mark.asyncio
async def test_register_reload_config_tool(mock_auth_provider: Any) -> None:
    """Test reload_config method is automatically registered as a tool.

    (covers line 215 in server.py).
    """

    # Create a ManagedServer subclass with reload_config method
    class CustomServer(ManagedServer):
        def reload_config(self) -> str:
            """Custom configuration reload method."""
            return "Configuration reloaded"

    # Use print capturing to verify reload_config method is registered
    with patch("builtins.print") as mock_print:
        # Create server instance
        server = CustomServer(
            name="reload-test",
            instructions="Test reload_config registration",
            auto_register=True,
            auth_server_provider=mock_auth_provider,
        )

        # Verify successful auto-registration print message
        found_print = False
        for call_args in mock_print.call_args_list:
            args = call_args[0]
            message = args[0] if args and isinstance(args[0], str) else ""
            if "Automatically registered" in message and "management tools" in message:
                found_print = True
                break

        assert found_print, "Print message about successful tool registration not found"

        # Verify reload_config method works correctly
        result = server.reload_config()
        assert result == "Configuration reloaded"


def test_managed_server_code_inspection() -> None:
    """Verify that server.py contains reload_config related logic through code inspection."""
    # Get ManagedServer._auto_register_management_tools source code
    source_code = inspect.getsource(ManagedServer._auto_register_management_tools)

    # Check if it contains code for registering reload_config method
    expected_code = "# Register custom reload_config method"
    assert expected_code in source_code, (
        "Comment about registering reload_config method doesn't exist in server.py"
    )

    # Check if it contains reload_config related code
    reload_config_code = "if hasattr(self, 'reload_config'):"
    assert reload_config_code in source_code, (
        "Code to check for reload_config method doesn't exist in server.py"
    )

    # Check if it contains code to wrap method as a tool function
    wrapping_code = "wrapped_reload_config()"
    assert wrapping_code in source_code, (
        "Code to wrap reload_config method doesn't exist in server.py"
    )

    # By reading the server class file, ensure the code contains expected content
    server_file = os.path.abspath(inspect.getfile(ManagedServer))
    with open(server_file) as f:
        content = f.read()

        # Verify file contains expected code
        assert expected_code in content, (
            "Comment about registering reload_config method doesn't exist in ManagedServer file"
        )
        assert reload_config_code in content, (
            "Code to check for reload_config method doesn't exist in ManagedServer file"
        )
        assert "manage_reload_config" in content, (
            "Tool name for registering reload_config doesn't exist in ManagedServer file"
        )


@pytest.mark.asyncio
async def test_reload_config_with_custom_path(mock_auth_provider: Any) -> None:
    """Test calling reload_config method with custom path parameter."""
    server = ManagedServer(
        name="reload-path-test",
        instructions="Configuration path test",
        auto_register=True,
        auth_server_provider=mock_auth_provider,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )

    # Capture output
    with patch("builtins.print") as mock_print:
        # Call reload_config with custom path
        result = server.reload_config(config_path="/custom/path/config.json")

        # Verify result contains custom path
        assert "Server configuration reloaded" in result
        assert "/custom/path/config.json" in result

        # Verify print output
        mock_print.assert_any_call(
            "Attempting to load configuration from /custom/path/config.json..."
        )


@pytest.mark.asyncio
async def test_reload_config_exception_handling(mock_auth_provider: Any) -> None:
    """Test exception handling in reload_config method."""
    server = ManagedServer(
        name="reload-error-test",
        instructions="Configuration error test",
        auto_register=True,
        auth_server_provider=mock_auth_provider,
        auth={
            "issuer_url": "https://example.auth0.com",
        },
    )

    # Use patch to simulate configuration loading exception
    def mock_load(*args: Any, **kwargs: Any) -> None:
        raise ValueError("Test exception")

    # Capture output and mock exception
    with patch("builtins.print") as mock_print, patch.object(
        server, "_load_config_from_file", side_effect=mock_load
    ), patch.object(server, "_load_default_config", side_effect=mock_load):
        # Call reload_config with default configuration path
        result = server.reload_config()

        # Verify result contains error message
        assert "Configuration reload failed" in result
        assert "Test exception" in result

        # Verify error message is printed
        mock_print.assert_any_call("Configuration reload failed: Test exception")

        # Test with custom path again
        result = server.reload_config("/custom/path/config.json")

        # Verify result still contains error message
        assert "Configuration reload failed" in result
        assert "Test exception" in result


# ... existing code ...
