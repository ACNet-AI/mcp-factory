"""Server edge case handling test module."""

import inspect
from unittest.mock import MagicMock, patch

import pytest

from fastmcp_factory.server import ManagedServer

# Set event loop scope for all tests
pytestmark = pytest.mark.asyncio(scope="function")


@pytest.mark.asyncio
async def test_auto_register_exception_handling() -> None:
    """Test exception handling during auto-registration (covers lines 167-169)."""
    mock_auth_provider = MagicMock()
    with patch("inspect.getmembers") as mock_getmembers:
        mock_getmembers.side_effect = Exception("Simulated scanning error")
        with patch("builtins.print") as mock_print:
            server = ManagedServer(
                name="error-test",
                instructions="Error test",
                auto_register=True,
                auth_server_provider=mock_auth_provider,
                auth={
                    "issuer_url": "https://example.auth0.com",
                },
            )
            mock_print.assert_any_call(
                "Error during auto-registration of management tools: Simulated scanning error"
            )
            mock_print.assert_any_call("Will continue but without management tool registration")
            assert server.name == "error-test"


@pytest.mark.asyncio
async def test_method_not_in_instance() -> None:
    """Test handling of methods not present in the instance (covers line 105)."""

    # Define a test class with a method not in ManagedServer
    class TestMethod:
        def unique_method(self) -> str:
            return "test"

    methods = inspect.getmembers(TestMethod, predicate=inspect.isfunction)
    # Use patch to replace inspect.getmembers
    mock_auth_provider = MagicMock()
    with patch("inspect.getmembers") as mock_getmembers:
        mock_getmembers.return_value = methods
        server = ManagedServer(
            name="missing-method-test",
            instructions="Missing method test",
            auto_register=True,
            auth_server_provider=mock_auth_provider,
            auth={
                "issuer_url": "https://example.auth0.com",
            },
        )
        assert server.name == "missing-method-test"
        tools = await server.get_tools()
        assert "manage_unique_method" not in tools


@pytest.mark.asyncio
async def test_method_registration_error() -> None:
    """Test error handling during method registration (covers lines 149-150)."""

    class TestManagedServer(ManagedServer):
        def problematic_method(self) -> None:
            """A test method that will cause registration issues."""
            pass

    mock_auth_provider = MagicMock()
    with patch.object(ManagedServer, "tool") as mock_tool:
        mock_tool.side_effect = Exception("Simulated registration error")
        with patch("builtins.print") as mock_print:
            server = TestManagedServer(
                name="registration-error-test",
                instructions="Registration error test",
                auto_register=True,
                auth_server_provider=mock_auth_provider,
                auth={
                    "issuer_url": "https://example.auth0.com",
                },
            )
            for call_args in mock_print.call_args_list:
                args, _ = call_args
                call_str = str(args[0]) if args else ""
                if "registering method" in call_str and "Simulated registration error" in call_str:
                    break
            else:
                assert False, "Expected error print not captured"

            assert server.name == "registration-error-test"


@pytest.mark.asyncio
async def test_wrapper_code_execution() -> None:
    """Test wrapper code execution part (covers lines 127-144)."""

    class TestManagedServer(ManagedServer):
        def test_sync_method(self, param1: str, param2: str) -> str:
            """A test synchronous method."""
            return f"Sync: {param1}, {param2}"

        async def test_async_method(self, param1: str, param2: str) -> str:
            """A test asynchronous method."""
            return f"Async: {param1}, {param2}"

    # Create method tuples list, simulating inspect.getmembers return format
    method_tuples = [
        ("test_sync_method", TestManagedServer.test_sync_method),
        ("test_async_method", TestManagedServer.test_async_method),
    ]

    mock_auth_provider = MagicMock()
    # Use patch to replace inspect.getmembers to return our test methods
    with patch("inspect.getmembers", return_value=method_tuples):
        server = TestManagedServer(
            name="wrapper-test",
            instructions="Wrapper function test",
            auto_register=True,
            auth_server_provider=mock_auth_provider,
            auth={
                "issuer_url": "https://example.auth0.com",
            },
        )
        tools = await server.get_tools()
        assert "manage_test_sync_method" in tools
        assert "manage_test_async_method" in tools
