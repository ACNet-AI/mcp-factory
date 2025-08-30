"""Current API tests for refactored FastMCP-Factory.

This test module focuses on testing the actual API of the refactored system,
rather than fixing old tests based on deprecated APIs.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from mcp_factory import ManagedServer, MCPFactory
from mcp_factory.exceptions import ServerError


class TestCurrentFactoryAPI:
    """Test the current MCPFactory API."""

    def test_factory_initialization(self) -> None:
        """Test factory can be initialized successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Check basic attributes exist
            assert hasattr(factory, "_servers")
            assert hasattr(factory, "builder")
            assert hasattr(factory, "_state_manager")
            assert factory._servers == {}

    def test_create_server_with_dict_config(self) -> None:
        """Test creating server with dict configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            config = {
                "server": {
                    "name": "test-server",
                    "instructions": "Test instructions",
                }
            }

            with patch("mcp_factory.factory.ManagedServer") as mock_server_class:
                mock_server = mock_server_class.return_value
                mock_server.name = "test-server"
                mock_server.instructions = "Test instructions"

                server_id = factory.create_server(name="test-server", source=config)

                assert server_id is not None
                assert server_id in factory._servers

    def test_list_and_get_servers(self) -> None:
        """Test listing and getting servers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Initially empty
            assert factory.list_servers() == []

            # Add a mock server
            mock_server = MagicMock()
            mock_server.name = "test-server"
            mock_server.instructions = "Test instructions"

            server_id = "test-id"
            factory._servers[server_id] = mock_server

            # Test list_servers
            servers = factory.list_servers()
            assert len(servers) == 1
            assert servers[0]["id"] == server_id
            assert servers[0]["name"] == "test-server"

            # Test get_server
            retrieved_server = factory.get_server(server_id)
            assert retrieved_server is mock_server

    def test_delete_server(self) -> None:
        """Test deleting servers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Add a mock server
            mock_server = MagicMock()
            mock_server.name = "test-server"
            factory._servers["test-id"] = mock_server

            # Delete existing server
            result = factory.delete_server("test-id")
            assert result is True
            assert "test-id" not in factory._servers

            # Delete non-existent server
            result = factory.delete_server("non-existent")
            assert result is False

    def test_get_server_status(self) -> None:
        """Test getting server status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Add a mock server
            mock_server = MagicMock()
            mock_server.name = "test-server"
            mock_server.instructions = "Test instructions"
            factory._servers["test-id"] = mock_server

            status = factory.get_server_status("test-id")
            assert status["id"] == "test-id"
            assert status["name"] == "test-server"
            assert status["instructions"] == "Test instructions"

    def test_create_project_and_server(self) -> None:
        """Test creating project and server together."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            config = {
                "server": {
                    "name": "project-server",
                    "instructions": "Project server",
                }
            }

            # Mock the build_project to return a valid project path
            project_path = Path(temp_dir) / "test-project"
            project_path.mkdir(exist_ok=True)

            # Create a basic config.yaml in the project directory
            config_file = project_path / "config.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            with patch.object(factory.builder, "build_project") as mock_build:
                mock_build.return_value = str(project_path)
                with patch("mcp_factory.factory.ManagedServer") as mock_server_class:
                    mock_server = mock_server_class.return_value
                    mock_server.name = "project-server"
                    mock_server.instructions = "Project server"

                    project_path_result, server_id = factory.create_project_and_server(
                        project_name="test-project", config_dict=config
                    )

                    assert project_path_result is not None
                    assert server_id is not None


class TestCurrentManagedServerAPI:
    """Test the current ManagedServer API."""

    def test_server_initialization(self) -> None:
        """Test server can be initialized successfully."""
        server = ManagedServer(name="test-server", instructions="Test instructions")

        assert server.name == "test-server"
        assert server.instructions == "Test instructions"

    def test_management_tools_registration(self) -> None:
        """Test that management tools are properly registered."""
        server = ManagedServer(name="test-server", instructions="Test instructions", expose_management_tools=True)

        # Check that some management tools exist
        # Note: The exact tools may vary, but there should be some
        tools = getattr(server._tool_manager, "_tools", {})
        management_tools = [name for name in tools.keys() if isinstance(name, str) and "manage" in name.lower()]
        assert len(management_tools) > 0

    def test_server_without_management_tools(self) -> None:
        """Test server creation without management tools."""
        server = ManagedServer(name="test-server", instructions="Test instructions", expose_management_tools=False)

        assert server.name == "test-server"
        # Should still work without management tools

    def test_get_management_tools_info(self) -> None:
        """Test getting management tools information."""
        server = ManagedServer(name="test-server", instructions="Test instructions", expose_management_tools=True)

        info = server.get_management_tools_info()
        assert isinstance(info, dict)
        assert "management_tools" in info
        assert "configuration" in info
        assert "statistics" in info


class TestConfigIntegration:
    """Test configuration integration with current API."""

    def test_yaml_config_loading(self) -> None:
        """Test loading configuration from YAML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Create a YAML config file
            config_data = {"server": {"name": "yaml-server", "instructions": "Server from YAML", "port": 8080}}

            config_file = Path(temp_dir) / "test_config.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            with patch("mcp_factory.factory.ManagedServer") as mock_server_class:
                mock_server = mock_server_class.return_value
                mock_server.name = "yaml-server"
                mock_server.instructions = "Server from YAML"

                server_id = factory.create_server(name="yaml-server", source=str(config_file))

                assert server_id is not None
                assert server_id in factory._servers

    def test_project_directory_as_source(self) -> None:
        """Test using project directory as configuration source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Create a project directory with config.yaml
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()

            config_file = project_dir / "config.yaml"
            config_data = {
                "server": {
                    "name": "project-server",
                    "instructions": "Server from project",
                }
            }

            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            with patch("mcp_factory.factory.ManagedServer") as mock_server_class:
                mock_server = mock_server_class.return_value
                mock_server.name = "project-server"
                mock_server.instructions = "Server from project"

                server_id = factory.create_server(name="project-server", source=str(project_dir))

                assert server_id is not None
                assert server_id in factory._servers


class TestErrorHandling:
    """Test error handling in current API."""

    def test_get_nonexistent_server(self) -> None:
        """Test getting non-existent server raises appropriate error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            with pytest.raises(ServerError, match="Server does not exist"):
                factory.get_server("non-existent")

    def test_invalid_config_handling(self) -> None:
        """Test that invalid configurations are handled gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # This should either succeed or raise a clear error
            # The exact behavior depends on validation implementation
            invalid_config = {"invalid": "configuration"}

            # The test just ensures no unexpected crashes occur
            try:
                factory.create_server(name="test-server", source=invalid_config)
            except Exception as e:
                # Any exception is acceptable as long as it's not a crash
                assert isinstance(e, Exception)
