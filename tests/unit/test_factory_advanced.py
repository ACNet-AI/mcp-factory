"""Unit test module for advanced functionality of FastMCPFactory."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_factory.factory import FastMCPFactory


class TestFactoryAdvancedFeatures:
    """Test advanced features of the factory class."""

    def test_init_with_config_file(self, tmp_path: Path) -> None:
        """Test initializing factory with configuration file."""
        # Create temporary configuration file
        config_path = tmp_path / "factory_config.yaml"
        config_content = """
        factory:
          default_server_settings:
            log_level: DEBUG
        """
        config_path.write_text(config_content)

        # Initialize factory with configuration file
        with patch("mcp_factory.config_validator.validate_config_file") as mock_validate:
            mock_validate.return_value = (
                True,
                {"factory": {"default_server_settings": {"log_level": "DEBUG"}}},
                [],
            )

            factory = FastMCPFactory(str(config_path))

            # Verify configuration validation was called
            mock_validate.assert_called_once_with(str(config_path))

            # Verify configuration was loaded
            assert factory._factory_config == {
                "factory": {"default_server_settings": {"log_level": "DEBUG"}}
            }

    def test_init_with_invalid_config_file(self, tmp_path: Path) -> None:
        """Test initializing factory with invalid configuration file."""
        # Create temporary configuration file
        config_path = tmp_path / "invalid_factory_config.yaml"
        config_content = """
        invalid_yaml: [
        """
        config_path.write_text(config_content)

        # Initialize factory with configuration file
        with patch("mcp_factory.config_validator.validate_config_file") as mock_validate:
            mock_validate.return_value = (False, {}, ["Invalid YAML format"])

            factory = FastMCPFactory(str(config_path))

            # Verify configuration validation was called
            mock_validate.assert_called_once_with(str(config_path))

            # Verify configuration was not loaded
            assert not hasattr(factory, "_factory_config") or factory._factory_config is None

    def test_init_with_nonexistent_config_file(self) -> None:
        """Test initializing factory with nonexistent configuration file."""
        # Use path to nonexistent configuration file
        nonexistent_path = "/path/does/not/exist/config.yaml"

        # Initialize factory
        factory = FastMCPFactory(nonexistent_path)

        # Verify configuration was not loaded
        assert not hasattr(factory, "_factory_config") or factory._factory_config is None

    def test_resolve_auth_provider_from_parameter(self) -> None:
        """Test resolving authentication provider from parameter."""
        factory = FastMCPFactory()

        # Create mock authentication provider
        mock_provider = MagicMock()
        mock_provider.domain = "example.auth0.com"

        # Mock authentication registry
        with patch.object(factory._auth_registry, "get_provider") as mock_get_provider:
            mock_get_provider.return_value = mock_provider

            # Call the method being tested
            provider = factory._resolve_auth_provider({}, "test-provider")

            # Verify results
            assert provider is mock_provider

            # Verify call
            mock_get_provider.assert_called_once_with("test-provider")

    def test_resolve_auth_provider_from_config(self) -> None:
        """Test resolving authentication provider from configuration."""
        factory = FastMCPFactory()

        # Create mock authentication provider
        mock_provider = MagicMock()
        mock_provider.domain = "example.auth0.com"

        # Create configuration
        config = {"auth": {"provider_id": "config-provider"}}

        # Mock authentication registry
        with patch.object(factory._auth_registry, "get_provider") as mock_get_provider:
            mock_get_provider.return_value = mock_provider

            # Call the method being tested
            provider = factory._resolve_auth_provider(config, None)

            # Verify results
            assert provider is mock_provider

            # Verify call
            mock_get_provider.assert_called_once_with("config-provider")

    def test_resolve_auth_provider_not_found(self) -> None:
        """Test resolving nonexistent authentication provider."""
        factory = FastMCPFactory()

        # Create configuration
        config = {"auth": {"provider_id": "nonexistent-provider"}}

        # Mock authentication registry
        with patch.object(factory._auth_registry, "get_provider") as mock_get_provider:
            mock_get_provider.return_value = None

            # Call the method being tested
            provider = factory._resolve_auth_provider(config, "nonexistent-provider")

            # Verify results
            assert provider is None

            # Verify call
            assert mock_get_provider.call_count == 2

    def test_process_advanced_params_empty(self) -> None:
        """Test processing empty advanced parameters."""
        factory = FastMCPFactory()

        # Call the method being tested
        result = factory._process_advanced_params({})

        # Verify results
        assert result == {}

    def test_process_advanced_params_with_lifespan(self) -> None:
        """Test processing advanced parameters with lifespan manager."""
        factory = FastMCPFactory()

        # Create mock lifespan manager
        mock_lifespan = MagicMock()

        # Call the method being tested
        result = factory._process_advanced_params({}, lifespan=mock_lifespan)

        # Verify results
        assert result["lifespan"] is mock_lifespan

    def test_process_advanced_params_with_tool_serializer(self) -> None:
        """Test processing advanced parameters with tool serializer."""
        factory = FastMCPFactory()

        # Create mock tool serializer
        mock_serializer = MagicMock()

        # Call the method being tested
        result = factory._process_advanced_params({}, tool_serializer=mock_serializer)

        # Verify results
        assert result["tool_serializer"] is mock_serializer

    def test_process_advanced_params_with_tags(self) -> None:
        """Test processing advanced parameters with tags."""
        factory = FastMCPFactory()

        # Create tag set
        api_tags = {"tag1", "tag2"}

        # Create configuration
        config = {"advanced": {"tags": ["tag2", "tag3"]}}

        # Call the method being tested
        with patch("mcp_factory.param_utils.merge_tags") as mock_merge:
            mock_merge.return_value = {"tag1", "tag2", "tag3"}

            result = factory._process_advanced_params(config, tags=api_tags)

            # Verify results
            assert result["tags"] == {"tag1", "tag2", "tag3"}

            # Verify call
            mock_merge.assert_called_once()

    def test_process_advanced_params_with_dependencies(self) -> None:
        """Test processing advanced parameters with dependencies."""
        factory = FastMCPFactory()

        # Create dependencies list
        api_deps = ["dep1", "dep2"]

        # Create configuration
        config = {"advanced": {"dependencies": ["dep2", "dep3"]}}

        # Call the method being tested
        with patch("mcp_factory.param_utils.merge_dependencies") as mock_merge:
            mock_merge.return_value = ["dep1", "dep2", "dep3"]

            result = factory._process_advanced_params(config, dependencies=api_deps)

            # Verify results
            assert result["dependencies"] == ["dep1", "dep2", "dep3"]

            # Verify call
            mock_merge.assert_called_once()

    def test_extract_base_params(self) -> None:
        """Test extracting basic parameters."""
        factory = FastMCPFactory()

        # Create server configuration
        server_config = {"name": "test-server", "instructions": "Test server instructions"}

        # Create override parameters
        override_params = {"instructions": "Override instructions"}

        # Call the method being tested
        result = factory._extract_base_params(server_config, override_params)

        # Verify results
        assert result["name"] == "test-server"
        assert result["instructions"] == "Override instructions"

    def test_extract_base_params_missing_required(self) -> None:
        """Test extracting basic parameters with missing required parameters."""
        factory = FastMCPFactory()

        # Create server configuration
        server_config = {"instructions": "Test server instructions"}

        # Create override parameters
        override_params = {}

        # Verify exception is raised when required parameters are missing
        with pytest.raises(ValueError):
            factory._extract_base_params(server_config, override_params)

    def test_delete_server(self) -> None:
        """Test deleting server."""
        factory = FastMCPFactory()

        # Create mock server
        mock_server = MagicMock()

        # Add to server dictionary
        factory._servers = {"test-server": mock_server}

        # Call the method being tested
        result = factory.delete_server("test-server")

        # Verify results
        assert "deleted" in result
        assert "test-server" in result
        assert "test-server" not in factory._servers

    def test_delete_nonexistent_server(self) -> None:
        """Test deleting nonexistent server."""
        factory = FastMCPFactory()

        # Clear server dictionary
        factory._servers = {}

        # Verify exception is raised when deleting nonexistent server
        with pytest.raises(ValueError) as excinfo:
            factory.delete_server("nonexistent-server")

        assert "not found" in str(excinfo.value)

    def test_prepare_server_params_complete(self) -> None:
        """Test preparing complete server parameters."""
        factory = FastMCPFactory()

        # Create configuration
        config = {
            "server": {"name": "test-server", "instructions": "Test server"},
            "auth": {"provider_id": "auth-provider"},
            "advanced": {"tags": ["tag1", "tag2"], "dependencies": ["dep1", "dep2"]},
        }

        # Mock authentication provider
        mock_provider = MagicMock()

        # Mock method
        with patch.object(factory, "_extract_base_params") as mock_extract:
            with patch.object(factory, "_resolve_auth_provider") as mock_resolve:
                with patch.object(factory, "_process_advanced_params") as mock_process:
                    # Set return value
                    mock_extract.return_value = {
                        "name": "test-server",
                        "instructions": "Test server",
                    }
                    mock_resolve.return_value = mock_provider
                    mock_process.return_value = {
                        "tags": {"tag1", "tag2"},
                        "dependencies": ["dep1", "dep2"],
                    }

                    # Call the method being tested
                    result = factory._prepare_server_params(
                        config=config,
                        expose_management_tools=True,
                        auth_provider_id="override-provider",
                        lifespan=None,
                        tags={"tag3"},
                        dependencies=["dep3"],
                        extra_param=123,
                    )

                    # Verify results
                    assert result["name"] == "test-server"
                    assert result["instructions"] == "Test server"
                    assert result["auth_server_provider"] is mock_provider
                    assert result["tags"] == {"tag1", "tag2"}
                    assert result["dependencies"] == ["dep1", "dep2"]
                    assert result["expose_management_tools"] is True
                    assert result["extra_param"] == 123

                    # Verify call
                    mock_extract.assert_called_once()
                    mock_resolve.assert_called_once_with(config, "override-provider")
                    mock_process.assert_called_once()

    def test_prepare_server_params_error(self) -> None:
        """Test preparing server parameters error."""
        factory = FastMCPFactory()

        # Create configuration
        config = {"server": {"name": "test-server"}}

        # Mock method throws exception
        with patch.object(factory, "_extract_base_params", side_effect=ValueError("Test error")):
            # Verify exception
            with pytest.raises(ValueError) as excinfo:
                factory._prepare_server_params(config)

            assert "Error preparing server parameters" in str(excinfo.value)

    def test_create_managed_server_full(self, tmp_path: Path) -> None:
        """Test complete server creation process."""
        factory = FastMCPFactory()

        # Create temporary configuration file
        config_path = tmp_path / "server_config.yaml"
        config_content = """
        server:
          name: test-server
          instructions: Test server instructions
        """
        config_path.write_text(config_content)

        # Mock configuration validation
        with patch("mcp_factory.config_validator.validate_config_file") as mock_validate:
            # Set return value
            mock_validate.return_value = (
                True,
                {"server": {"name": "test-server", "instructions": "Test server instructions"}},
                [],
            )

            # Mock _prepare_server_params method
            with patch.object(factory, "_prepare_server_params") as mock_prepare:
                # Set return value
                server_params = {
                    "name": "test-server",
                    "instructions": "Test server instructions",
                    "expose_management_tools": True,
                }
                mock_prepare.return_value = server_params

                # Mock ManagedServer
                mock_server = MagicMock()
                mock_server.name = "test-server"

                # Mock ManagedServer creation
                with patch(
                    "mcp_factory.factory.ManagedServer", return_value=mock_server
                ) as mock_server_cls:
                    # Call the method being tested
                    server = factory.create_managed_server(str(config_path))

                    # Verify results
                    assert server is mock_server
                    assert "test-server" in factory._servers
                    assert factory._servers["test-server"] is mock_server

                    # Verify call
                    mock_validate.assert_called_once()
                    mock_prepare.assert_called_once()
                    mock_server_cls.assert_called_once_with(**server_params)
                    mock_server.apply_config.assert_called_once()

    def test_create_managed_server_invalid_config(self, tmp_path: Path) -> None:
        """Test creating server with invalid configuration."""
        factory = FastMCPFactory()

        # Create temporary configuration file
        config_path = tmp_path / "invalid_server_config.yaml"
        config_content = """
        invalid_yaml: [
        """
        config_path.write_text(config_content)

        # Mock configuration validation
        with patch("mcp_factory.config_validator.validate_config_file") as mock_validate:
            # Set return value
            mock_validate.return_value = (False, {}, ["Invalid YAML format"])

            # Verify exception is raised
            with pytest.raises(ValueError) as excinfo:
                factory.create_managed_server(str(config_path))

            assert "Invalid server configuration" in str(excinfo.value)

    def test_create_managed_server_creation_error(self, tmp_path: Path) -> None:
        """Test server creation error."""
        factory = FastMCPFactory()

        # Create temporary configuration file
        config_path = tmp_path / "server_config.yaml"
        config_content = """
        server:
          name: test-server
          instructions: Test server instructions
        """
        config_path.write_text(config_content)

        # Mock configuration validation
        with patch("mcp_factory.config_validator.validate_config_file") as mock_validate:
            # Set return value
            mock_validate.return_value = (
                True,
                {"server": {"name": "test-server", "instructions": "Test server instructions"}},
                [],
            )

            # Mock _prepare_server_params method
            with patch.object(factory, "_prepare_server_params") as mock_prepare:
                # Set return value
                server_params = {
                    "name": "test-server",
                    "instructions": "Test server instructions",
                    "expose_management_tools": True,
                }
                mock_prepare.return_value = server_params

                # Mock ManagedServer creation failure
                with patch(
                    "mcp_factory.factory.ManagedServer",
                    side_effect=ValueError("Server creation error"),
                ):
                    # Verify exception is raised
                    with pytest.raises(ValueError) as excinfo:
                        factory.create_managed_server(str(config_path))

                    assert "Failed to create server" in str(excinfo.value)


class TestAuthProviderManagement:
    """Test authentication provider management functionality."""

    def test_create_auth_provider(self) -> None:
        """Test creating authentication provider."""
        factory = FastMCPFactory()

        # Create mock authentication provider
        mock_provider = MagicMock()

        # Create provider configuration
        provider_config = {
            "domain": "example.auth0.com",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
        }

        # Mock authentication registry creation method
        with patch.object(factory._auth_registry, "create_provider") as mock_create:
            # Set return value
            mock_create.return_value = mock_provider

            # Call the method being tested
            provider = factory.create_auth_provider(
                provider_id="test-provider", provider_type="auth0", config=provider_config
            )

            # Verify results
            assert provider is mock_provider

            # Verify call
            mock_create.assert_called_once_with(
                provider_id="test-provider", provider_type="auth0", config=provider_config
            )

    def test_create_auth_provider_failure(self) -> None:
        """Test creating authentication provider failure."""
        factory = FastMCPFactory()

        # Create provider configuration
        provider_config = {
            "domain": "example.auth0.com",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
        }

        # Mock authentication registry creation method
        with patch.object(factory._auth_registry, "create_provider") as mock_create:
            # Set return value
            mock_create.return_value = None

            # Call the method being tested
            provider = factory.create_auth_provider(
                provider_id="test-provider", provider_type="auth0", config=provider_config
            )

            # Verify results
            assert provider is None

            # Verify call
            mock_create.assert_called_once_with(
                provider_id="test-provider", provider_type="auth0", config=provider_config
            )

    def test_get_auth_provider(self) -> None:
        """Test getting authentication provider."""
        factory = FastMCPFactory()

        # Create mock authentication provider
        mock_provider = MagicMock()

        # Mock authentication registry get method
        with patch.object(factory._auth_registry, "get_provider") as mock_get:
            # Set return value
            mock_get.return_value = mock_provider

            # Call the method being tested
            provider = factory.get_auth_provider("test-provider")

            # Verify results
            assert provider is mock_provider

            # Verify call
            mock_get.assert_called_once_with("test-provider")

    def test_get_nonexistent_auth_provider(self) -> None:
        """Test getting nonexistent authentication provider."""
        factory = FastMCPFactory()

        # Mock authentication registry get method
        with patch.object(factory._auth_registry, "get_provider") as mock_get:
            # Set return value
            mock_get.return_value = None

            # Call the method being tested
            provider = factory.get_auth_provider("nonexistent-provider")

            # Verify results
            assert provider is None

            # Verify call
            mock_get.assert_called_once_with("nonexistent-provider")

    def test_list_auth_providers(self) -> None:
        """Test listing all authentication providers."""
        factory = FastMCPFactory()

        # Create provider list
        providers = {"provider1": "auth0", "provider2": "oauth"}

        # Mock authentication registry list method
        with patch.object(factory._auth_registry, "list_providers") as mock_list:
            # Set return value
            mock_list.return_value = providers

            # Call the method being tested
            result = factory.list_auth_providers()

            # Verify results
            assert result == providers
            assert "provider1" in result
            assert result["provider1"] == "auth0"
            assert "provider2" in result
            assert result["provider2"] == "oauth"

            # Verify call
            mock_list.assert_called_once()

    def test_list_empty_auth_providers(self) -> None:
        """Test listing empty authentication provider list."""
        factory = FastMCPFactory()

        # Mock authentication registry list method
        with patch.object(factory._auth_registry, "list_providers") as mock_list:
            # Set return value
            mock_list.return_value = {}

            # Call the method being tested
            result = factory.list_auth_providers()

            # Verify results
            assert result == {}

            # Verify call
            mock_list.assert_called_once()

    def test_remove_auth_provider(self) -> None:
        """Test removing authentication provider."""
        factory = FastMCPFactory()

        # Mock authentication registry remove method
        with patch.object(factory._auth_registry, "remove_provider") as mock_remove:
            # Set return value
            mock_remove.return_value = True

            # Call the method being tested
            result = factory.remove_auth_provider("test-provider")

            # Verify results
            assert result is True

            # Verify call
            mock_remove.assert_called_once_with("test-provider")

    def test_remove_nonexistent_auth_provider(self) -> None:
        """Test removing nonexistent authentication provider."""
        factory = FastMCPFactory()

        # Mock authentication registry remove method
        with patch.object(factory._auth_registry, "remove_provider") as mock_remove:
            # Set return value
            mock_remove.return_value = False

            # Call the method being tested
            result = factory.remove_auth_provider("nonexistent-provider")

            # Verify results
            assert result is False

            # Verify call
            mock_remove.assert_called_once_with("nonexistent-provider")
