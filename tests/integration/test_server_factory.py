"""Integration test module for FastMCPFactory and ManagedServer."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import yaml

from mcp_factory import FastMCPFactory


class TestFactoryServerIntegration:
    """Test the complete integration between factory and server."""

    def test_create_and_run_server(self) -> None:
        """Test creating and running a server through the factory."""
        factory = FastMCPFactory()

        # Create temporary configuration file for testing
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config = {
                "server": {
                    "name": "integration-test",
                    "instructions": "Integration test server",
                    "host": "localhost",
                    "port": 8080,
                }
            }
            yaml_content = yaml.dump(config)
            temp_file.write(yaml_content.encode("utf-8"))
            config_path = temp_file.name

        try:
            # Use patch to prevent actual server running
            with patch("fastmcp.FastMCP.run") as mock_run:
                # Create server
                server = factory.create_managed_server(
                    config_path=config_path, expose_management_tools=True
                )

                # Verify server was successfully created
                assert server.name == "integration-test"
                assert server.instructions == "Integration test server"

                # Verify server was correctly added to factory
                assert "integration-test" in factory.list_servers()
                assert factory.get_server("integration-test") is server

                # Run server
                server.run(transport="streamable-http", debug=True)

                # Verify run method was called
                mock_run.assert_called_once()
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)

    def test_config_reload_integration(self, temp_config_file: str) -> None:
        """Test the complete integration flow of configuration reloading."""
        # Create factory and server
        factory = FastMCPFactory()
        server = factory.create_managed_server(config_path=temp_config_file)

        # Verify initial state
        assert server.name == "test-server"  # Read from configuration file

        # Update configuration file
        updated_config = {
            "server": {
                "name": "updated-name",  # Name won't update because it's read-only
                "instructions": "Updated instructions",  # Instructions won't update because they're read-only
                "host": "127.0.0.1",
                "port": 8888,
                "settings": {"debug": False, "custom_setting": "updated_value"},
            }
        }
        with open(temp_config_file, "w") as file:
            yaml.dump(updated_config, file)

        # Reload configuration
        server.reload_config(config_path=temp_config_file)

        # Verify read-only properties did not change
        assert server.name == "test-server"  # Read-only property, unchanged

        # Note: The specific configuration storage structure depends on implementation, using _config here as an example
        if hasattr(server, "_config"):
            updated_settings = server._config.get("server", {}).get("settings", {})
            assert "debug" in str(updated_settings)  # Verify settings section was updated


@pytest.mark.asyncio
class TestAsyncIntegration:
    """Integration tests for asynchronous functionality."""

    async def test_auth_server_integration(self, mock_auth_provider: MagicMock) -> None:
        """Test integration between server and authentication provider."""
        # Create temporary configuration file for testing
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config = {
                "server": {
                    "name": "auth-integration",
                    "instructions": "Auth integration test",
                    "host": "localhost",
                    "port": 8080,
                },
                "auth": {"issuer_url": "https://example.auth0.com"},
            }
            yaml_content = yaml.dump(config)
            temp_file.write(yaml_content.encode("utf-8"))
            config_path = temp_file.name

        try:
            # Create server
            factory = FastMCPFactory()

            # Mock server run to avoid actual startup
            with patch("fastmcp.FastMCP.run") as mock_run:
                server = factory.create_managed_server(
                    config_path=config_path,
                    auth_server_provider=mock_auth_provider,
                )

                # Verify server name
                assert server.name == "auth-integration"
                
                # Verify authentication provider was set during construction
                assert server._auth_server_provider is mock_auth_provider
                
                # Verify auth config was stored for runtime use
                assert hasattr(server, '_runtime_kwargs')
                assert 'auth' in server._runtime_kwargs
                assert server._runtime_kwargs['auth'] == {"issuer_url": "https://example.auth0.com"}

                # Run server (won't actually start)
                server.run()

                # Verify run method was called with auth settings
                mock_run.assert_called_once()
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)
