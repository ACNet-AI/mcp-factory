"""Unit test module for configuration validation and processing."""

import os
import tempfile

import yaml

from mcp_factory import config_validator


class TestConfigValidation:
    """Test configuration file validation functionality."""

    def test_valid_config_validation(self) -> None:
        """Test validation of valid configuration files."""
        # Create valid configuration file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            valid_config = {
                "server": {
                    "name": "test-server",
                    "instructions": "Test server configuration",
                    "host": "localhost",
                    "port": 8080,
                },
                "auth": {"issuer_url": "https://example.auth0.com"},
            }
            yaml_content = yaml.dump(valid_config)
            temp_file.write(yaml_content.encode("utf-8"))
            valid_config_path = temp_file.name

        try:
            # Test valid configuration validation
            is_valid, config, errors = config_validator.validate_config_file(valid_config_path)
            assert is_valid is True
            assert not errors
            assert config["server"]["name"] == "test-server"
        finally:
            # Clean up temporary file
            if os.path.exists(valid_config_path):
                os.unlink(valid_config_path)

    def test_invalid_config_validation(self) -> None:
        """Test validation of invalid configuration files."""
        # Create invalid configuration file - missing required server field
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            invalid_config = {
                # Completely missing server section
                "name": "test-server",
                "auth": {"issuer_url": "https://example.auth0.com"},
            }
            yaml_content = yaml.dump(invalid_config)
            temp_file.write(yaml_content.encode("utf-8"))
            invalid_config_path = temp_file.name

        try:
            # Test invalid configuration validation
            is_valid, config, errors = config_validator.validate_config_file(invalid_config_path)
            assert is_valid is False
            assert len(errors) > 0
            # Verify errors include missing server field
            found_server_error = False
            for error in errors:
                if "server" in error:
                    found_server_error = True
                    break
            assert found_server_error, "Should include error about missing server field"
        finally:
            # Clean up temporary file
            if os.path.exists(invalid_config_path):
                os.unlink(invalid_config_path)

    def test_malformed_yaml_validation(self) -> None:
        """Test validation of malformed YAML configuration files."""
        # Create malformed YAML file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            invalid_yaml = """
            server:
              name: "test-server
              instructions: "Missing end quote
              port: [1, 2, 3
            """
            temp_file.write(invalid_yaml.encode("utf-8"))
            malformed_path = temp_file.name

        try:
            # Test validation of malformed configuration
            is_valid, config, errors = config_validator.validate_config_file(malformed_path)
            assert is_valid is False
            assert len(errors) > 0
            # YAML errors might include various different formats in error messages
            assert any(
                (
                    "yaml" in error.lower()
                    or "YAML" in error
                    or "parse" in error
                    or "format" in error
                )
                for error in errors
            ), "Should include information about YAML format errors"
        finally:
            # Clean up temporary file
            if os.path.exists(malformed_path):
                os.unlink(malformed_path)

    def test_nonexistent_config_file(self) -> None:
        """Test handling of nonexistent configuration files."""
        # Use a path that definitely doesn't exist
        nonexistent_path = "/path/does/not/exist/config.yaml"

        # Test validation of nonexistent configuration file
        is_valid, config, errors = config_validator.validate_config_file(nonexistent_path)

        # Verify results
        assert is_valid is False
        assert len(errors) > 0
        assert any("exist" in error or "not found" in error for error in errors), (
            "Should include error about file not existing"
        )

    def test_get_default_config(self) -> None:
        """Test the get default configuration functionality."""
        # Get default configuration
        default_config = config_validator.get_default_config()

        # Verify default configuration structure
        assert isinstance(default_config, dict)
        assert "server" in default_config
        assert "name" in default_config["server"]
        assert "instructions" in default_config["server"]

        # Verify default values
        assert default_config["server"]["name"] == "default-mcp-server"
        # Check that instructions exist but don't compare specific content, as it may change
        assert default_config["server"]["instructions"]

        # Verify other default sections
        assert "advanced" in default_config
        assert "log_level" in default_config["advanced"]
        assert default_config["advanced"]["log_level"] == "INFO"

        # Verify auth section
        if "auth" in default_config:
            assert isinstance(default_config["auth"], dict)

    def test_server_name_missing(self) -> None:
        """Test the case of missing server name."""
        # Create configuration missing server name
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config = {
                "server": {
                    # Missing name field
                    "instructions": "Test server",
                    "host": "localhost",
                    "port": 8080,
                }
            }
            yaml_content = yaml.dump(config)
            temp_file.write(yaml_content.encode("utf-8"))
            config_path = temp_file.name

        try:
            # Validate configuration
            is_valid, loaded_config, errors = config_validator.validate_config_file(config_path)

            # Verify results
            assert is_valid is False
            assert len(errors) > 0
            assert any("name" in error.lower() for error in errors), (
                "Should include error about missing name"
            )
        finally:
            # Clean up temporary file
            if os.path.exists(config_path):
                os.unlink(config_path)

    def test_config_validation_directly(self) -> None:
        """Directly test the configuration validation function."""
        # Test valid configuration
        valid_config = {"server": {"name": "test-server", "instructions": "Test server"}}
        is_valid, errors = config_validator.validate_config(valid_config)
        assert is_valid is True
        assert len(errors) == 0

        # Test invalid configuration - empty configuration
        invalid_config = {}
        is_valid, errors = config_validator.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
        assert "empty" in errors[0]

        # Test invalid configuration - missing server section
        invalid_config = {"other": "value"}
        is_valid, errors = config_validator.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0

        # Test invalid configuration - empty server name
        invalid_config = {"server": {"name": ""}}
        is_valid, errors = config_validator.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
        assert any("name" in error for error in errors)

    def test_load_config_yaml_error(self) -> None:
        """Test handling of YAML errors when loading configuration."""
        # Create configuration file with YAML format error
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            invalid_yaml = """
            server: {
              "name": "test-server",
              invalid syntax here
              "port": 8080
            }
            """
            temp_file.write(invalid_yaml.encode("utf-8"))
            config_path = temp_file.name

        try:
            # Test configuration validation rather than direct loading
            is_valid, config, errors = config_validator.validate_config_file(config_path)
            assert is_valid is False
            assert len(errors) > 0
            assert any(
                (
                    "yaml" in error.lower()
                    or "YAML" in error
                    or "parse" in error
                    or "format" in error
                )
                for error in errors
            )
        finally:
            # Clean up temporary file
            if os.path.exists(config_path):
                os.unlink(config_path)

    def test_tools_config_validation(self) -> None:
        """Test validation of tool configuration options."""
        # Create configuration file including tool configuration options
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config = {
                "server": {"name": "tools-test-server", "instructions": "Tool configuration test"},
                "tools": {
                    "expose_management_tools": True,
                    "enabled_tools": ["tool1", "tool2", "tool3"],
                    "tool_permissions": {
                        "tool1": {"requiresAuth": False},
                        "tool2": {"requiresAuth": True, "adminOnly": False},
                        "tool3": {"requiresAuth": True, "adminOnly": True, "destructiveHint": True},
                    },
                },
            }
            yaml_content = yaml.dump(config)
            temp_file.write(yaml_content.encode("utf-8"))
            config_path = temp_file.name

        try:
            # Validate configuration
            is_valid, loaded_config, errors = config_validator.validate_config_file(config_path)

            # Verify results
            assert is_valid is True
            assert not errors

            # Verify tool configuration
            assert "tools" in loaded_config
            tools_config = loaded_config["tools"]

            # Verify expose_management_tools
            assert tools_config["expose_management_tools"] is True

            # Verify enabled_tools
            assert "enabled_tools" in tools_config
            assert len(tools_config["enabled_tools"]) == 3
            assert "tool1" in tools_config["enabled_tools"]

            # Verify tool_permissions
            assert "tool_permissions" in tools_config
            permissions = tools_config["tool_permissions"]
            assert "tool1" in permissions
            assert permissions["tool1"]["requiresAuth"] is False
            assert "tool3" in permissions
            assert permissions["tool3"]["adminOnly"] is True
        finally:
            # Clean up temporary file
            if os.path.exists(config_path):
                os.unlink(config_path)


class TestConfigBasics:
    """Test configuration basic functionality."""

    def test_load_config(self) -> None:
        """Test the load configuration file functionality."""
        # Create valid configuration file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config = {
                "server": {
                    "name": "test-server",
                    "instructions": "Test instructions",
                    "host": "127.0.0.1",
                    "port": 8080,
                }
            }
            yaml_content = yaml.dump(config)
            temp_file.write(yaml_content.encode("utf-8"))
            config_path = temp_file.name

        try:
            # Use validation function directly load configuration
            is_valid, loaded_config, errors = config_validator.validate_config_file(config_path)

            # Verify loaded configuration
            assert is_valid is True
            assert loaded_config["server"]["name"] == "test-server"
            assert loaded_config["server"]["port"] == 8080
        finally:
            # Clean up temporary file
            if os.path.exists(config_path):
                os.unlink(config_path)

    def test_empty_config(self) -> None:
        """Test handling of empty configuration files."""
        # Create empty configuration file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            temp_file.write(b"")
            empty_config_path = temp_file.name

        try:
            # Test empty configuration validation
            is_valid, config, errors = config_validator.validate_config_file(empty_config_path)
            assert is_valid is False
            assert len(errors) > 0
        finally:
            # Clean up temporary file
            if os.path.exists(empty_config_path):
                os.unlink(empty_config_path)


class TestConfigAdvanced:
    """Test advanced configuration functionality."""

    def test_config_sections(self) -> None:
        """Test the various sections in the configuration."""
        # Create configuration file with multiple sections
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            config = {
                "server": {
                    "name": "multi-section",
                    "instructions": "Multi-section test",
                    "host": "localhost",
                    "port": 8080,
                },
                "auth": {
                    "issuer_url": "https://example.auth0.com",
                    "audience": "https://api.example.com",
                },
                "tools": {"enabled": True, "prefix": "mcp_"},
            }
            yaml_content = yaml.dump(config)
            temp_file.write(yaml_content.encode("utf-8"))
            config_path = temp_file.name

        try:
            # Verify configuration
            is_valid, loaded_config, errors = config_validator.validate_config_file(config_path)

            # Verify all sections exist
            assert is_valid is True
            assert "server" in loaded_config
            assert "auth" in loaded_config
            assert "tools" in loaded_config

            # Verify section contents
            assert loaded_config["server"]["name"] == "multi-section"
            assert loaded_config["auth"]["issuer_url"] == "https://example.auth0.com"
            assert loaded_config["tools"]["enabled"] is True
        finally:
            # Clean up temporary file
            if os.path.exists(config_path):
                os.unlink(config_path)
