"""Unit Test module for MCPFactory class."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from mcp_factory import MCPFactory
from mcp_factory.exceptions import ProjectError, ServerError, ValidationError
from mcp_factory.factory import ComponentRegistry, ServerStateManager


class TestFactoryBasics:
    """Test basic functionality of MCPFactory."""

    def test_factory_initialization(self) -> None:
        """Test factory initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize factory with a clean directory
            factory = MCPFactory(workspace_root=temp_dir)

            # Verify basic attributes exist
            assert hasattr(factory, "_state_manager")
            assert hasattr(factory, "builder")
            assert hasattr(factory, "_servers")  # Should exist but might have loaded servers

    def test_factory_with_workspace_root(self) -> None:
        """Test factory Create with workspace root."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)
            assert isinstance(factory, MCPFactory)
            assert str(factory.workspace_root) == temp_dir


class TestServerManagement:
    """Test server management functionality."""

    def test_server_registration(self) -> None:
        """Test server registration and retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Clear any existing servers for clean Test
            factory._servers.clear()

            # Create Mock server
            mock_server = MagicMock()
            mock_server.name = "Test-server"
            mock_server.instructions = "Test server"

            # Manually register server
            factory._servers["Test-server"] = mock_server

            # Verify server retrieval
            assert factory.get_server("Test-server") is mock_server

            # Verify server appears in list
            server_list = factory.list_servers()
            assert len(server_list) == 1
            assert server_list[0]["id"] == "Test-server"
            assert server_list[0]["name"] == "Test-server"

    def test_server_removal(self) -> None:
        """Test server removal functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Add two Mock servers to the factory
            mock_server1 = MagicMock()
            mock_server1.name = "server1"
            mock_server1.instructions = "Server 1"
            mock_server2 = MagicMock()
            mock_server2.name = "server2"
            mock_server2.instructions = "Server 2"

            factory._servers = {"server1": mock_server1, "server2": mock_server2}

            # Verify server list
            server_list = factory.list_servers()
            server_ids = [s["id"] for s in server_list]
            assert "server1" in server_ids
            assert "server2" in server_ids

            # Test deleting an existing server
            result = factory.delete_server("server1")
            assert result is True
            assert "server1" not in factory._servers
            assert "server2" in factory._servers

            # Test deleting a nonexistent server
            result = factory.delete_server("nonexistent")
            assert result is False


class TestServerCreation:
    """Test server Create functionality."""

    def test_create_server_with_config_file(self) -> None:
        """Test creating server with a configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Create temporary configuration file
            with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
                config = {
                    "server": {
                        "name": "Test-server",
                        "instructions": "Test server description",
                        "host": "127.0.0.1",
                        "port": 8000,
                    },
                }
                yaml_content = yaml.dump(config)
                temp_file.write(yaml_content.encode("utf-8"))
                config_path = temp_file.name

            try:
                # Use temporary configuration file path to create server
                with patch("mcp_factory.factory.ManagedServer") as mock_server_class:
                    mock_server = mock_server_class.return_value
                    mock_server.name = "Test-server"
                    mock_server.instructions = "Test server description"

                    # Call create method (updated method name)
                    server_id = factory.create_server(
                        name="Test-server",
                        source=config_path,
                        expose_management_tools=True,
                    )

                    # Verify server was created and registered
                    assert server_id is not None
                    # Server ID is a UUID, so Check if a server with this ID exists
                    assert server_id in factory._servers
                    # Verify the server name is correct
                    created_server = factory.get_server(server_id)
                    assert created_server.name == "Test-server"
            finally:
                # Clean up temporary file
                os.unlink(config_path)

    def test_server_name_from_config(self) -> None:
        """Test reading server name from configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Create temporary configuration file
            with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
                config = {
                    "server": {
                        "name": "config-name-server",
                        "instructions": "Server created with names from config",
                        "host": "localhost",
                        "port": 8080,
                    },
                }
                yaml_content = yaml.dump(config)
                temp_file.write(yaml_content.encode("utf-8"))
                config_path = temp_file.name

            try:
                # Create server using configuration file
                with patch("mcp_factory.factory.ManagedServer") as mock_server_class:
                    # Set name attribute for Mock server
                    mock_server = mock_server_class.return_value
                    mock_server.name = "config-name-server"
                    mock_server.instructions = "Server created with names from config"

                    # Create server (updated method name)
                    server_id = factory.create_server(name="config-name-server", source=config_path)

                    # Verify server name
                    assert server_id is not None
                    server = factory.get_server(server_id)
                    assert server.name == "config-name-server"
            finally:
                # Clean up temporary file
                if os.path.exists(config_path):
                    os.unlink(config_path)

    def test_get_server_nonexistent(self) -> None:
        """Test getting a nonexistent server raises ServerError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            with pytest.raises(ServerError, match="Server does not exist"):
                factory.get_server("nonexistent")

    def test_get_server_status(self) -> None:
        """Test getting server status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Create Mock server
            mock_server = MagicMock()
            mock_server.name = "Test-server"
            mock_server.instructions = "Test server"
            factory._servers["Test-server"] = mock_server

            status = factory.get_server_status("Test-server")
            assert status["id"] == "Test-server"
            assert status["name"] == "Test-server"
            assert status["instructions"] == "Test server"


class TestComponentRegistry:
    """Test ComponentRegistry functionality."""

    def test_register_components_no_config(self) -> None:
        """Test component registration with no components config."""
        mock_server = MagicMock()
        mock_server._config = {}

        from mcp_factory.factory import ComponentRegistry

        # Should not raise exception
        ComponentRegistry.register_components(mock_server, Path("/fake/path"))

    def test_register_components_empty_config(self) -> None:
        """Test component registration with empty components config."""
        mock_server = MagicMock()
        mock_server._config = {"components": {}}

        from mcp_factory.factory import ComponentRegistry

        # Should not raise exception
        ComponentRegistry.register_components(mock_server, Path("/fake/path"))

    def test_load_component_functions_nonexistent_file(self) -> None:
        """Test loading component functions from nonexistent file."""
        from mcp_factory.factory import ComponentRegistry

        functions = ComponentRegistry._load_component_functions(Path("/fake/path"), "tools", "nonexistent_module")
        assert functions == []

    def test_register_functions_to_server(self) -> None:
        """Test registering functions to server."""
        from mcp_factory.factory import ComponentRegistry

        mock_server = MagicMock()

        def test_func() -> None:
            """Test function"""

        functions = [(test_func, "test_func", "Test function")]

        # Test tool registration
        count = ComponentRegistry._register_functions_to_server(mock_server, "tools", functions)
        assert count == 1
        mock_server.tool.assert_called_once()

        # Test with server without resource method
        mock_server.reSet_Mock()
        del mock_server.resource  # Remove resource method
        count = ComponentRegistry._register_functions_to_server(mock_server, "resources", functions)
        assert count == 0


class TestServerStateManager:
    """Test ServerStateManager functionality."""

    @pytest.fixture
    def sample_config(self):
        """Sample server configuration"""
        return {
            "server": {
                "name": "test-server",
                "instructions": "Test instructions",
                "expose_management_tools": True,
            },
            "project_path": "/test/project",
        }

    def test_initialize_server_state(self, sample_config) -> None:
        """Test server state initialization."""
        from mcp_factory.factory import ServerStateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            state_manager = ServerStateManager(Path(temp_dir))

            state_manager.initialize_server_state("test-server", "Test Server", sample_config)

            # Check summary
            summary = state_manager.get_servers_summary()
            assert "test-server" in summary
            assert summary["test-server"]["status"] == "created"

            # Check legacy compatibility
            state = state_manager.get_server_state("test-server")
            assert state["status"] == "created"
            assert "created_at" in state

    def test_update_server_state(self, sample_config) -> None:
        """Test updating server state."""
        from mcp_factory.factory import ServerStateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            state_manager = ServerStateManager(Path(temp_dir))

            state_manager.initialize_server_state("test-server", "Test Server", sample_config)
            state_manager.update_server_state("test-server", status="running", event="server_started")

            # Check summary updated
            summary = state_manager.get_servers_summary()
            assert summary["test-server"]["status"] == "running"

            # Check legacy compatibility
            state = state_manager.get_server_state("test-server")
            assert state["status"] == "running"

    def test_get_nonexistent_server_state(self) -> None:
        """Test getting state for nonexistent server."""
        from mcp_factory.factory import ServerStateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            state_manager = ServerStateManager(Path(temp_dir))

            state = state_manager.get_server_state("nonexistent")
            assert state == {}

    def test_remove_server_state(self, sample_config) -> None:
        """Test removing server state."""
        from mcp_factory.factory import ServerStateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            state_manager = ServerStateManager(Path(temp_dir))

            state_manager.initialize_server_state("test-server", "Test Server", sample_config)
            state_manager.remove_server_state("test-server")

            # Check removed from summary
            summary = state_manager.get_servers_summary()
            assert "test-server" not in summary

            # Check legacy compatibility
            state = state_manager.get_server_state("test-server")
            assert state == {}

    def test_dual_storage_architecture(self, sample_config) -> None:
        """Test dual storage architecture functionality."""
        from mcp_factory.factory import ServerStateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)
            state_manager = ServerStateManager(workspace_path)

            # Initialize server
            state_manager.initialize_server_state("test-server", "Test Server", sample_config)

            # Check summary file exists
            summary_file = workspace_path / ".servers_state.json"
            assert summary_file.exists()

            # Check detail file exists
            detail_file = workspace_path / ".states" / "test-server.json"
            assert detail_file.exists()

            # Verify new state manager can load existing data
            new_state_manager = ServerStateManager(workspace_path)
            summary = new_state_manager.get_servers_summary()
            assert "test-server" in summary
            assert summary["test-server"]["name"] == "Test Server"


class TestFactoryErrorHandling:
    """Test error handling in factory operations."""

    def test_create_server_with_invalid_config(self) -> None:
        """Test creating server with truly invalid configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        # Create a config that normalize_config can't fix and will still fail validation
        # Use invalid YAML structure or missing critical fields
        with patch("mcp_factory.factory.validate_config") as mock_validate:
            mock_validate.return_value = (False, ["Configuration validation failed"])

            with pytest.raises(ValidationError):  # Should raise ValidationError
                factory.create_server(
                    name="Test-server",
                    source={"server": {"name": "Test"}},  # This would normally be valid
                )

    def test_update_nonexistent_server(self) -> None:
        """Test updating nonexistent server."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        with pytest.raises(ServerError, match="Server does not exist"):
            factory.update_server("nonexistent", name="new-name")

    def test_reload_nonexistent_server(self) -> None:
        """Test restarting nonexistent server."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        with pytest.raises(ServerError, match="Server does not exist"):
            factory.restart_server("nonexistent")

    def test_get_status_nonexistent_server(self) -> None:
        """Test getting status of nonexistent server."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        with pytest.raises(ServerError, match="Server does not exist"):
            factory.get_server_status("nonexistent")


class TestFactoryProjectIntegration:
    """Test factory integration with project building."""

    def test_build_project(self) -> None:
        """Test building project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            with patch.object(factory.builder, "build_project") as mock_build:
                mock_build.return_value = "/fake/project/path"

                project_path = factory.build_project("Test-project", {})
                assert project_path == "/fake/project/path"
                mock_build.assert_called_once()

    def test_create_project_and_server(self) -> None:
        """Test creating project and server together."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            config = {"server": {"name": "Test-server", "instructions": "Test instructions"}}

            # Create a real project directory to Mock
            project_path = Path(temp_dir) / "Test-project"
            project_path.mkdir(parents=True, exist_ok=True)
            config_file = project_path / "config.yaml"

            with (
                patch.object(factory.builder, "build_project") as mock_build,
                patch("mcp_factory.factory.ManagedServer") as mock_server_class,
            ):
                mock_build.return_value = str(project_path)
                mock_server = mock_server_class.return_value
                mock_server.name = "Test-server"
                mock_server.instructions = "Test instructions"

                # Create a config file in the project directory
                with open(config_file, "w") as f:
                    yaml.dump(config, f)

                project_path_result, server_id = factory.create_project_and_server("Test-project", config)

                assert project_path_result == str(project_path)
                assert server_id in factory._servers

    def test_sync_to_project_functionality(self) -> None:
        """Test sync to project functionality that replaces save_config_to_project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Create a project and server first
            project_path, server_id = factory.create_project_and_server(
                "Test-sync-project",
                {"server": {"name": "Test-sync", "instructions": "Test sync"}},
            )

            # Sync should work correctly
            result = factory.sync_to_project(server_id)
            assert result is True


class TestServerStateManagerFileOperations:
    """Test ServerStateManager file operation functionality for new architecture"""

    @pytest.fixture
    def sample_config(self):
        """Sample server configuration"""
        return {
            "server": {
                "name": "test-server",
                "instructions": "Test instructions",
                "expose_management_tools": True,
            },
            "project_path": "/test/project",
        }

    def test_atomic_file_operations(self, sample_config) -> None:
        """Test atomic file operations in new architecture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)
            manager = ServerStateManager(workspace_path)

            # Initialize server - should create files atomically
            manager.initialize_server_state("server1", "Server One", sample_config)

            # Verify files exist and temp files are cleaned up
            summary_file = workspace_path / ".servers_state.json"
            detail_file = workspace_path / ".states" / "server1.json"

            assert summary_file.exists()
            assert detail_file.exists()

            # Ensure no temp files left behind
            assert not (workspace_path / ".servers_state.tmp").exists()
            assert not (workspace_path / ".states" / "server1.tmp").exists()

    def test_concurrent_state_updates(self, sample_config) -> None:
        """Test that state updates don't corrupt files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)
            manager = ServerStateManager(workspace_path)

            # Initialize multiple servers
            manager.initialize_server_state("server1", "Server One", sample_config)
            manager.initialize_server_state("server2", "Server Two", sample_config)

            # Update states rapidly
            for i in range(5):
                manager.update_server_state("server1", status="running", event=f"update_{i}")
                manager.update_server_state("server2", status="stopped", event=f"update_{i}")

            # Verify both servers have consistent state
            summary = manager.get_servers_summary()
            assert summary["server1"]["status"] == "running"
            assert summary["server2"]["status"] == "stopped"

            # Verify detailed history
            history1 = manager.get_server_history("server1")
            history2 = manager.get_server_history("server2")
            assert len(history1) == 6  # Initial + 5 updates
            assert len(history2) == 6  # Initial + 5 updates

    def test_error_handling_in_file_operations(self, sample_config) -> None:
        """Test error handling during file operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)
            manager = ServerStateManager(workspace_path)

            # Initialize server normally
            manager.initialize_server_state("server1", "Server One", sample_config)

            # Test error handling with file permission issues
            with patch("mcp_factory.factory.logger") as mock_logger:
                with patch("builtins.open", side_effect=OSError("Permission denied")):
                    # This should log error but not crash
                    manager.update_server_state("server1", status="running")

                # Verify error was logged
                mock_logger.error.assert_called()

    def test_state_persistence_across_restarts(self, sample_config) -> None:
        """Test that state persists across manager restarts"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            # Create first manager and add data
            manager1 = ServerStateManager(workspace_path)
            manager1.initialize_server_state("server1", "Server One", sample_config)
            manager1.update_server_state("server1", status="running", event="startup")

            # Create second manager - should load existing data
            manager2 = ServerStateManager(workspace_path)
            summary = manager2.get_servers_summary()

            assert "server1" in summary
            assert summary["server1"]["name"] == "Server One"
            assert summary["server1"]["status"] == "running"

            # Verify detailed state also loaded
            details = manager2.get_server_details("server1")
            assert details["current_status"] == "running"
            assert len(details["state_history"]) == 2  # Initial + update

    def test_corrupted_summary_file_handling(self, sample_config) -> None:
        """Test handling of corrupted summary files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)
            summary_file = workspace_path / ".servers_state.json"

            # Create corrupted summary file
            with open(summary_file, "w") as f:
                f.write("invalid json content")

            # Manager should handle this gracefully
            with patch("mcp_factory.factory.logger") as mock_logger:
                manager = ServerStateManager(workspace_path)
                mock_logger.error.assert_called()

            # Should start with empty state
            summary = manager.get_servers_summary()
            assert len(summary) == 0


class TestComponentRegistryAdvanced:
    """Test ComponentRegistry advancedfunction"""

    def test_register_components_with_config(self) -> None:
        """Test component registration with configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create Mock tool module
            tools_dir = project_path / "tools"
            tools_dir.mkdir()

            tool_file = tools_dir / "sample.py"
            tool_file.write_text('''
def sample_tool():
    """This is an example tool"""
    return "Hello from tool"

def _private_function():
    """Private function, should not be registered"""
    return "private"
''')

            # Create Mock server
            mock_server = MagicMock()
            mock_server._config = {"components": {"tools": [{"module": "sample", "enabled": True}]}}

            # Register components
            ComponentRegistry.register_components(mock_server, project_path)

            # Verify tool was registered
            mock_server.tool.assert_called()

    def test_register_components_no_components_config(self) -> None:
        """Test component registration without components configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create Mock server without components configuration
            mock_server = MagicMock()
            mock_server._config = {}

            # Component registration should not perform any operation
            ComponentRegistry.register_components(mock_server, project_path)

            # Verify no registration methods were called
            mock_server.tool.assert_not_called()

    def test_register_components_with_error(self) -> None:
        """Test error handling during component registration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create problematic Mock server (without _config attribute)
            mock_server = MagicMock()
            del mock_server._config  # Remove _config attribute

            # Should catch exception and continue
            ComponentRegistry.register_components(mock_server, project_path)
            # If no exception is thrown, test passes

    def test_load_component_functions_spec_create_error(self) -> None:
        """Test module specification creation error"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create empty tool file
            tools_dir = project_path / "tools"
            tools_dir.mkdir()
            empty_file = tools_dir / "empty.py"
            empty_file.write_text("")

            # Use patch to Mock spec creation failure
            with patch("importlib.util.spec_from_file_location", return_value=None):
                functions = ComponentRegistry._load_component_functions(project_path, "tools", "empty")

                # Should return empty list
                assert functions == []

    def test_load_component_functions_loader_none(self) -> None:
        """Test module loading when spec.loader is None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create tool file
            tools_dir = project_path / "tools"
            tools_dir.mkdir()
            tool_file = tools_dir / "Test.py"
            tool_file.write_text("def test_func(): pass")

            # Mock spec with None loader
            mock_spec = MagicMock()
            mock_spec.loader = None

            with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
                functions = ComponentRegistry._load_component_functions(project_path, "tools", "Test")

                # Should return empty list
                assert functions == []

    def test_register_functions_to_server_resources(self) -> None:
        """Test registering resource functions to server"""
        mock_server = MagicMock()
        mock_server.resource = MagicMock()

        def sample_resource() -> str:
            """Example resource"""
            return "resource data"

        functions = [(sample_resource, "sample_resource", "Example resource")]

        count = ComponentRegistry._register_functions_to_server(mock_server, "resources", functions)

        assert count == 1
        mock_server.resource.assert_called_once()

    def test_register_functions_to_server_prompts(self) -> None:
        """Test registering prompt functions to server"""
        mock_server = MagicMock()
        mock_server.prompt = MagicMock()

        def sample_prompt() -> str:
            """Example prompt"""
            return "prompt text"

        functions = [(sample_prompt, "sample_prompt", "Example prompt")]

        count = ComponentRegistry._register_functions_to_server(mock_server, "prompts", functions)

        assert count == 1
        mock_server.prompt.assert_called_once()

    def test_register_functions_server_without_method(self) -> None:
        """Test server without corresponding method situation"""
        mock_server = MagicMock()
        # Don't set resource method
        del mock_server.resource

        def sample_resource() -> str:
            return "data"

        functions = [(sample_resource, "sample_resource", "description")]

        count = ComponentRegistry._register_functions_to_server(mock_server, "resources", functions)

        # Should skip registration
        assert count == 0

    def test_register_functions_with_registration_error(self) -> None:
        """Test error handling when registering functions"""
        mock_server = MagicMock()
        mock_server.tool.side_effect = Exception("register failure")

        def sample_tool() -> str:
            return "tool"

        functions = [(sample_tool, "sample_tool", "description")]

        # Should catch exception and continue
        count = ComponentRegistry._register_functions_to_server(mock_server, "tools", functions)

        assert count == 0


class TestFactoryAdvancedServerManagement:
    """Test Factory advancedservermanagementfunction"""

    def test_update_server(self) -> None:
        """Test update server"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        # Create mock server
        mock_server = MagicMock()
        mock_server.name = "Test-server"
        factory._servers["Test-server"] = mock_server

        # Update server
        updated_server = factory.update_server("Test-server", name="new-name")

        # Verify returned updated server
        assert updated_server is mock_server

    def test_reload_server_config(self) -> None:
        """Test reloading server configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        # Create Mock server
        mock_server = MagicMock()
        mock_server.name = "Test-server"
        factory._servers["Test-server"] = mock_server

        # Reload configuration
        reloaded_server = factory.reload_server_config("Test-server")

        # Verify returned server
        assert reloaded_server is mock_server

    def test_reload_nonexistent_server_config(self) -> None:
        """Test reloading nonexistent server configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        with pytest.raises(ServerError, match="Server does not exist"):
            factory.reload_server_config("nonexistent")

    def test_restart_server(self) -> None:
        """Test restart server"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        # Create mock server
        mock_server = MagicMock()
        mock_server.name = "Test-server"
        factory._servers["Test-server"] = mock_server

        # Restart server
        restarted_server = factory.restart_server("Test-server")

        # Verify returned server
        assert restarted_server is mock_server

    def test_restart_nonexistent_server(self) -> None:
        """Test restart nonexistent server"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        with pytest.raises(ServerError, match="Server does not exist"):
            factory.restart_server("nonexistent")

    def test_get_server_status_with_state(self) -> None:
        """Test get server state with state"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        # Create mock server
        mock_server = MagicMock()
        mock_server.name = "Test-server"
        mock_server.instructions = "Test instructions"
        factory._servers["Test-server"] = mock_server

        # Add state information
        config = {"server": {"name": "Test-server", "instructions": "Test instructions"}}
        factory._state_manager.initialize_server_state("Test-server", "Test-server", config)
        factory._state_manager.update_server_state("Test-server", status="running")

        # Get state
        status = factory.get_server_status("Test-server")

        # Verify state information structure
        assert status["id"] == "Test-server"
        assert status["name"] == "Test-server"
        assert status["instructions"] == "Test instructions"
        assert "state" in status
        # State information is in state field
        assert status["state"]["status"] == "running"

    def test_get_nonexistent_server_status(self) -> None:
        """Test get nonexistent server state"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        with pytest.raises(ServerError, match="Server does not exist"):
            factory.get_server_status("nonexistent")


class TestFactoryProjectOperations:
    """Test Factory project operation functions"""

    def test_build_project_with_config(self) -> None:
        """Test building project with configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            config_dict = {"server": {"name": "Test-project", "instructions": "Test project"}}

            # Use patch to Mock builder.build_project
            with patch.object(factory.builder, "build_project") as mock_build:
                mock_build.return_value = "project_path"

                result = factory.build_project("Test-project", config_dict)

                assert result == "project_path"
                mock_build.assert_called_once_with("Test-project", config_dict, False)

    def test_build_project_without_config(self) -> None:
        """Test building project without configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Use patch to Mock builder.build_project
            with patch.object(factory.builder, "build_project") as mock_build:
                mock_build.return_value = "project_path"

                result = factory.build_project("Test-project")

                assert result == "project_path"
                mock_build.assert_called_once_with("Test-project", None, False)

    def test_create_project_and_server_success(self) -> None:
        """Test creating project and server successfully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            config_dict = {"server": {"name": "Test-project-server", "instructions": "Test project server"}}

            # Mock build_project and create_server
            with (
                patch.object(factory, "build_project") as mock_build,
                patch.object(factory, "create_server") as mock_create,
            ):
                mock_build.return_value = "project_path"
                mock_create.return_value = "server_id"

                project_path, server_id = factory.create_project_and_server("Test-project", config_dict)

                assert project_path == "project_path"
                assert server_id == "server_id"


class TestFactoryConfigHandling:
    """Test Factory configuration processing functions"""

    def test_load_config_from_dict(self) -> None:
        """Test loading configuration from dictionary"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        config_dict = {"server": {"name": "dict-server", "instructions": "From dict"}}

        result = factory._load_config_from_source(config_dict)
        assert result == config_dict

    def test_load_config_from_path_object(self) -> None:
        """Test loading configuration from Path object"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {"server": {"name": "path-server"}}
            yaml.dump(config, f)
            config_path = f.name

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                factory = MCPFactory(workspace_root=temp_dir)
            result = factory._load_config_from_source(Path(config_path))
            assert result["server"]["name"] == "path-server"
        finally:
            os.unlink(config_path)

    def test_load_config_from_string_path(self) -> None:
        """Test loading configuration from string path"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {"server": {"name": "string-path-server"}}
            yaml.dump(config, f)
            config_path = f.name

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                factory = MCPFactory(workspace_root=temp_dir)
            result = factory._load_config_from_source(config_path)
            assert result["server"]["name"] == "string-path-server"
        finally:
            os.unlink(config_path)

    def test_apply_all_params(self) -> None:
        """Test applying all parameters"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        config = {"server": {"instructions": "original"}}
        server_kwargs = {"host": "localhost", "port": 8080}

        factory._apply_all_params(config, "Test-server", True, server_kwargs)

        # Verify parameters were applied
        assert config["server"]["name"] == "Test-server"
        assert config["server"]["host"] == "localhost"
        assert config["server"]["port"] == 8080

    def test_validate_config_success(self) -> None:
        """Test configuration validation success"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        config = {"server": {"name": "valid-server", "instructions": "Valid configuration"}}

        # Use patch to Mock normalize_config and validate_config
        with (
            patch("mcp_factory.factory.normalize_config") as mock_normalize,
            patch("mcp_factory.factory.validate_config") as mock_validate,
        ):
            mock_normalize.return_value = config
            mock_validate.return_value = (True, [])

            result = factory._validate_config(config)
            assert result == config

    def test_validate_config_failure(self) -> None:
        """Test configuration validation failure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        config = {"server": {"name": ""}}  # Invalid configuration

        # Use patch to Mock validation failure
        with (
            patch("mcp_factory.factory.normalize_config") as mock_normalize,
            patch("mcp_factory.factory.validate_config") as mock_validate,
        ):
            mock_normalize.return_value = config
            mock_validate.return_value = (False, ["name cannot be empty"])

            with pytest.raises(ValidationError):
                factory._validate_config(config)


class TestFactoryStateManagement:
    """Test advanced state management functionality."""

    def test_complete_operation(self) -> None:
        """Test completing operations with state updates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Create a Mock server and initialize state first
            mock_server = MagicMock()
            mock_server.name = "Test-server"
            factory._servers["Test-server"] = mock_server

            # Initialize server state (required by new architecture)
            config = {"server": {"name": "Test-server"}}
            factory._state_manager.initialize_server_state("Test-server", "Test-server", config)

            # Test completing an operation
            factory._complete_operation("Test-server", "test_operation", "Test operation completed")

            # Verify state was updated with the operation event
            details = factory._state_manager.get_server_details("Test-server")
            assert details is not None
            assert "state_history" in details
            # Check if operation was logged in history
            assert len(details["state_history"]) > 0

    def test_save_servers_state(self) -> None:
        """Test saving servers state to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Add Mock server with initialization of state (required in new architecture)
            mock_server = MagicMock()
            mock_server.name = "Test-server"
            mock_server.instructions = "Test instructions"
            factory._servers["Test-server"] = mock_server

            # Initialize state to trigger file creation
            config = {"server": {"name": "Test-server", "instructions": "Test instructions"}}
            factory._state_manager.initialize_server_state("Test-server", "Test-server", config)

            # Verify summary file exists (new architecture)
            summary_file = factory.workspace_root / ".servers_state.json"
            assert summary_file.exists()

    def test_load_servers_state_file_exists(self) -> None:
        """Test loading servers state when file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Create detailed state data first (required by new architecture)
            detailed_state = {
                "name": "Test-server",
                "config": {
                    "server": {
                        "name": "Test-server",
                        "instructions": "Test instructions",
                    },
                },
                "created_at": 1234567890.0,
                "state_history": [],
            }

            # Write detailed state file
            states_dir = factory.workspace_root / ".states"
            states_dir.mkdir(exist_ok=True)
            with open(states_dir / "Test-server.json", "w") as f:
                json.dump(detailed_state, f)

            # Create Mock state data for new architecture
            summary_data = {
                "Test-server": {
                    "name": "Test-server",
                    "status": "created",
                    "created_at": 1234567890.0,
                    "last_updated": 1234567890.0,
                    "project_path": None,
                },
            }

            # Write summary state file (new architecture)
            summary_file = factory.workspace_root / ".servers_state.json"
            with open(summary_file, "w") as f:
                json.dump(summary_data, f)

            # Load state (this happens in init, so create new factory)
            with patch.object(factory, "_create_server_from_state_data") as mock_create:
                # Mock both methods needed by _load_servers_state
                with patch.object(factory._state_manager, "get_servers_summary", return_value=summary_data):
                    with patch.object(factory._state_manager, "get_server_details", return_value=detailed_state):
                        factory._load_servers_state()
                        # Verify create method was called for each server
                        assert mock_create.call_count == 1

    def test_create_server_from_data(self) -> None:
        """Test creating server from saved data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            server_data = {
                "name": "Test-server",
                "instructions": "Test instructions",
                "project_path": None,
                "config": {"server": {"name": "Test-server", "instructions": "Test instructions"}},
                "expose_management_tools": True,
            }

            with patch("mcp_factory.factory.ManagedServer") as mock_server_class:
                mock_server = mock_server_class.return_value
                mock_server.name = "Test-server"
                mock_server.instructions = "Test instructions"

                # Test creating server from data
                result = factory._create_server_from_data("Test-server", server_data)

                # Verify server was created
                assert result is mock_server
                assert mock_server_class.called


class TestComponentRegistryErrorHandling:
    """Test ComponentRegistry error handling paths."""

    def test_load_component_functions_importlib_exception(self) -> None:
        """Test module loading with importlib exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            tools_dir = project_path / "tools"
            tools_dir.mkdir()

            # Create a Python file with syntax error
            bad_module = tools_dir / "bad_module.py"
            bad_module.write_text("def bad_function(:\n    pass  # syntax error")

            # Test loading the bad module
            from mcp_factory.factory import ComponentRegistry

            functions = ComponentRegistry._load_component_functions(project_path, "tools", "bad_module")

            # Should return empty list due to exception
            assert functions == []

    def test_load_component_functions_spec_none(self) -> None:
        """Test module loading when spec is None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            tools_dir = project_path / "tools"
            tools_dir.mkdir()

            # Create a normal Python file
            Test_module = tools_dir / "Test_module.py"
            Test_module.write_text("def test_function():\n    return 'Test'")

            # Mock spec_from_file_location to return None
            from mcp_factory.factory import ComponentRegistry

            with patch("importlib.util.spec_from_file_location", return_value=None):
                functions = ComponentRegistry._load_component_functions(project_path, "tools", "Test_module")

                # Should return empty list
                assert functions == []

    def test_load_component_functions_loader_none(self) -> None:
        """Test module loading when spec.loader is None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            tools_dir = project_path / "tools"
            tools_dir.mkdir()

            # Create a normal Python file
            Test_module = tools_dir / "Test_module.py"
            Test_module.write_text("def test_function():\n    return 'Test'")

            # Mock spec with None loader
            mock_spec = MagicMock()
            mock_spec.loader = None

            from mcp_factory.factory import ComponentRegistry

            with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
                functions = ComponentRegistry._load_component_functions(project_path, "tools", "Test_module")

                # Should return empty list
                assert functions == []

    def test_register_components_exception_handling(self) -> None:
        """Test register_components exception handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create Mock server
            mock_server = MagicMock()

            from mcp_factory.factory import ComponentRegistry

            # Mock _load_component_functions to raise exception
            with patch.object(ComponentRegistry, "_load_component_functions", side_effect=Exception("Test error")):
                # Should not raise exception, just log error
                ComponentRegistry.register_components(mock_server, project_path)

    def test_register_functions_to_server_registration_exception(self) -> None:
        """Test function registration with server exception."""
        mock_server = MagicMock()
        # Make server.tool() raise exception
        mock_server.tool.side_effect = Exception("Registration failed")

        def test_func() -> str:
            """Test function"""
            return "Test"

        functions = [(test_func, "test_func", "Test function")]

        from mcp_factory.factory import ComponentRegistry

        registered_count = ComponentRegistry._register_functions_to_server(mock_server, "tools", functions)

        # Should return 0 due to registration failure
        assert registered_count == 0

    def test_register_functions_unknown_component_type(self) -> None:
        """Test registering functions with unknown component type."""
        mock_server = MagicMock()

        def test_func() -> str:
            """Test function"""
            return "Test"

        functions = [(test_func, "test_func", "Test function")]

        from mcp_factory.factory import ComponentRegistry

        registered_count = ComponentRegistry._register_functions_to_server(mock_server, "unknown_type", functions)

        # Should return 0 for unknown type
        assert registered_count == 0


class TestFactoryInitializationErrors:
    """Test factory initialization error cases."""

    def test_factory_initialization_exception(self) -> None:
        """Test factory initialization with exception."""
        # Mock Path to raise exception
        with patch("mcp_factory.factory.Path") as mock_path:
            mock_path.side_effect = Exception("Path Create failed")

            with pytest.raises(Exception, match="Path Create failed"):
                MCPFactory(workspace_root="/invalid/path")

    def test_factory_load_servers_state_exception(self) -> None:
        """Test factory initialization with state loading exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create invalid JSON file
            state_file = Path(temp_dir) / ".servers_state.json"
            state_file.write_text("invalid json content")

            # Factory should still initialize despite invalid state file
            factory = MCPFactory(workspace_root=temp_dir)
            assert isinstance(factory, MCPFactory)

    def test_create_server_error_handler_called(self) -> None:
        """Test that error handler is called on create_server failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Mock _load_config_from_source to raise exception
            with patch.object(factory, "_load_config_from_source", side_effect=Exception("Config load failed")):
                with patch.object(factory._error_handler, "handle_error") as mock_handle:
                    # Should call error handler and return None
                    result = factory.create_server("Test", {"server": {"name": "Test"}})

                    # Verify error handler was called
                    mock_handle.assert_called_once()
                    # Verify None was returned
                    assert result is None

    def test_delete_server_error_handler_called(self) -> None:
        """Test that error handler is called on delete_server failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        # Add Mock server that will cause exception on deletion
        mock_server = MagicMock()
        mock_server.name = "Test-server"
        factory._servers["Test-server"] = mock_server

        # Mock remove_server_state to raise exception (this is what actually gets called in new architecture)
        with patch.object(factory._state_manager, "remove_server_state", side_effect=Exception("State removal failed")):
            with patch.object(factory._error_handler, "handle_error") as mock_handle:
                # Should call error handler and return False
                result = factory.delete_server("Test-server")

                # Verify error handler was called
                mock_handle.assert_called_once()
                # Verify False was returned due to error
                assert result is False


class TestFactoryAdvancedErrorScenarios:
    """Test advanced error scenarios in factory operations."""

    def test_update_server_error_handler(self) -> None:
        """Test update_server error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

        # Add Mock server
        mock_server = MagicMock()
        mock_server.name = "Test-server"
        factory._servers["Test-server"] = mock_server

        # Mock _complete_operation to raise exception, test error handling in try block
        with patch.object(factory, "_complete_operation", side_effect=Exception("Operation failed")):
            with patch.object(factory._error_handler, "handle_error") as mock_handle:
                # Now error handler will record error and then re-throw exception
                with pytest.raises(Exception, match="Operation failed"):
                    factory.update_server("Test-server", instructions="new instructions")

                # Verify error handler was called
                mock_handle.assert_called_once()

    def test_reload_server_config_no_project_path(self) -> None:
        """Test reload_server_config when server has no project path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            server_id = factory.create_server("Test-server", {"server": {"name": "Test"}})

            with pytest.raises(ServerError, match="has no associated project path"):
                factory.reload_server_config(server_id)

    def test_restart_server_success(self) -> None:
        """Test successful server restart"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Create a project directory
            project_path = Path(temp_dir) / "Test_project"
            project_path.mkdir()

            server_id = factory.create_server("Test-server", {"server": {"name": "Test"}})
            server = factory.get_server(server_id)
            server._project_path = str(project_path)

            # Restart server
            restarted_server = factory.restart_server(server_id)
            assert restarted_server is not None

    def test_sync_to_project_no_project_path(self) -> None:
        """Test sync to project when server has no project path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            server_id = factory.create_server("Test-server", {"server": {"name": "Test"}})

            result = factory.sync_to_project(server_id)
            assert result is False

    def test_sync_to_project_nonexistent_path(self) -> None:
        """Test sync to project with nonexistent target path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            server_id = factory.create_server("Test-server", {"server": {"name": "Test"}})

            result = factory.sync_to_project(server_id, "/nonexistent/path")
            assert result is False

    def test_load_config_from_source_dict(self) -> None:
        """Test loading config from dictionary source"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            config_dict = {"server": {"name": "Test"}}
            result = factory._load_config_from_source(config_dict)
            assert result == config_dict

    def test_load_config_from_source_directory_no_config(self) -> None:
        """Test loading config from directory without config file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            # Create empty directory
            project_path = Path(temp_dir) / "empty_project"
            project_path.mkdir()

            result = factory._load_config_from_source(project_path)
            # Should return default config
            assert isinstance(result, dict)
            assert "server" in result

    def test_load_config_from_source_nonexistent_path(self) -> None:
        """Test loading config from nonexistent path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            with pytest.raises(ProjectError, match="Source path does not exist"):
                factory._load_config_from_source("/nonexistent/path")

    def test_apply_all_params_streamable_features(self) -> None:
        """Test applying streamable parameters"""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = MCPFactory(workspace_root=temp_dir)

            config = {}
            server_kwargs = {
                "host": "0.0.0.0",
                "port": 9000,
                "streamable_output": True,
                "streamable_tools": ["tool1"],
                "custom_param": "value",
            }

            factory._apply_all_params(config, "Test", True, server_kwargs)

            assert config["server"]["host"] == "0.0.0.0"
            assert config["server"]["port"] == 9000
            assert config["advanced"]["streamable_output"] is True
            assert config["advanced"]["streamable_tools"] == ["tool1"]
