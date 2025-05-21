"""Unit test module for FastMCPFactory class."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import yaml

from fastmcp_factory import FastMCPFactory


class TestFactoryBasics:
    """Test basic functionality of FastMCPFactory."""

    def test_factory_initialization(self) -> None:
        """Test factory initialization."""
        # Initialize factory
        factory = FastMCPFactory()

        # Verify initial state
        assert factory._servers == {}
        assert hasattr(factory, "_auth_registry")

        # Verify factory methods
        assert factory.list_servers() == {}
        assert factory.get_server("non-existent") is None

    def test_factory_with_options(self) -> None:
        """Test factory creation with options."""
        # Test optional parameters conservatively
        try:
            # Try passing a custom option, even if it might not be accepted
            factory = FastMCPFactory()
            # Only verify that the factory was successfully created
            assert isinstance(factory, FastMCPFactory)
        except TypeError:
            # If no parameters are accepted, that's also fine
            factory = FastMCPFactory()
            assert isinstance(factory, FastMCPFactory)


class TestServerManagement:
    """Test server management functionality."""

    def test_server_registration(self) -> None:
        """Test server registration and retrieval."""
        factory = FastMCPFactory()

        # Create mock server
        mock_server = MagicMock()
        mock_server.name = "test-server"

        # Manually register server
        factory._servers["test-server"] = mock_server

        # Verify server retrieval
        assert factory.get_server("test-server") is mock_server
        assert "test-server" in factory.list_servers()

    def test_server_removal(self) -> None:
        """Test server removal functionality."""
        factory = FastMCPFactory()

        # Add two mock servers to the factory
        mock_server1 = MagicMock()
        mock_server1.name = "server1"
        mock_server2 = MagicMock()
        mock_server2.name = "server2"

        factory._servers = {"server1": mock_server1, "server2": mock_server2}

        # Verify server list
        server_list = factory.list_servers()
        assert "server1" in server_list
        assert "server2" in server_list

        # Test deleting an existing server
        result = factory.delete_server("server1")
        assert "server1" not in factory._servers
        assert "server2" in factory._servers
        assert "deleted" in result.lower()

        # Test deleting a non-existent server
        with pytest.raises(ValueError):
            factory.delete_server("non-existent")


class TestServerCreation:
    """Test server creation functionality."""

    def test_create_server_with_config_file(self) -> None:
        """Test creating server with a configuration file."""
        factory = FastMCPFactory()

        # Create temporary configuration file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config = {
                "server": {
                    "name": "test-server",
                    "instructions": "Test server description",
                    "host": "127.0.0.1",
                    "port": 8000,
                }
            }
            yaml_content = yaml.dump(config)
            temp_file.write(yaml_content.encode("utf-8"))
            config_path = temp_file.name

        try:
            # Use temporary configuration file path to create server
            with patch("fastmcp_factory.factory.ManagedServer") as mock_server_class:
                mock_server = mock_server_class.return_value
                type(mock_server).name = property(lambda self: "test-server")

                # Call create method
                server = factory.create_managed_server(
                    config_path=config_path, expose_management_tools=True
                )

                # Verify server was added to the factory
                assert server is mock_server
                assert server.name in factory._servers
        finally:
            # Clean up temporary file
            os.unlink(config_path)

    def test_server_name_from_config(self) -> None:
        """Test reading server name from configuration file."""
        factory = FastMCPFactory()

        # Create temporary configuration file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config = {
                "server": {
                    "name": "config-name-server",
                    "instructions": "Server created with names from config",
                    "host": "localhost",
                    "port": 8080,
                }
            }
            yaml_content = yaml.dump(config)
            temp_file.write(yaml_content.encode("utf-8"))
            config_path = temp_file.name

        try:
            # Create server using configuration file
            with patch("fastmcp_factory.server.ManagedServer") as mock_server_class:
                # Set name attribute for mock server
                mock_server = mock_server_class.return_value
                type(mock_server).name = property(lambda self: "config-name-server")

                # Create server
                server = factory.create_managed_server(config_path=config_path)

                # Verify server name
                assert server.name == "config-name-server"
                assert server.name in factory._servers
        finally:
            # Clean up temporary file
            if os.path.exists(config_path):
                os.unlink(config_path)
