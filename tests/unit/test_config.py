"""Configuration system unit tests"""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from mcp_factory.config import (
    SERVER_CONFIG_SCHEMA,
    detect_config_format,
    get_default_config,
    load_config_file,
    load_config_from_string,
    merge_configs,
    normalize_config,
    save_config_file,
    update_config,
    validate_config,
    validate_config_file,
)
from mcp_factory.exceptions import ConfigurationError


class TestDefaultConfig:
    """Test default configuration generation"""

    def test_get_default_config_basic(self):
        """Test get basic default configuration"""
        config = get_default_config()

        assert isinstance(config, dict)
        assert "server" in config
        assert "name" in config["server"]
        assert "instructions" in config["server"]

    def test_get_default_config_structure(self):
        """Test default configuration structure"""
        config = get_default_config()

        # Verify structure completeness
        assert "server" in config
        assert "transport" in config
        assert "management" in config

        # Verify specific fields
        assert config["server"]["name"] == "Default Server"
        assert config["server"]["instructions"] == "This is a default MCP server"
        assert config["transport"]["transport"] == "stdio"
        assert config["management"]["expose_management_tools"] is True


class TestConfigNormalization:
    """Test configuration normalization"""

    def test_normalize_config_with_top_level_name(self):
        """Test normalize top-level name field"""
        config = {"name": "test-server"}
        normalized = normalize_config(config)

        assert "server" in normalized
        assert normalized["server"]["name"] == "test-server"
        assert "name" not in normalized

    def test_normalize_config_with_description_only(self):
        """Test normalize configuration with description only"""
        config = {"description": "test description"}
        normalized = normalize_config(config)

        assert "server" in normalized
        assert normalized["server"]["name"] == "unnamed-server"
        assert normalized["description"] == "test description"

    def test_normalize_config_with_existing_server(self):
        """Test normalize configuration with existing server field"""
        config = {"server": {"instructions": "test"}}
        normalized = normalize_config(config)

        assert normalized["server"]["name"] == "unnamed-server"
        assert normalized["server"]["instructions"] == "test"

    def test_normalize_config_with_complete_server(self):
        """Test normalize complete server configuration (no modification needed)"""
        config = {"server": {"name": "test-server", "instructions": "test"}}
        normalized = normalize_config(config)

        assert normalized == config  # should remain unchanged

    def test_normalize_then_validate(self):
        """Test normalization followed by validation process"""
        problematic_configs = [
            {"name": "test"},
            {"description": "test desc"},
            {"name": "test", "auth": {"provider": "none"}},
        ]

        for config in problematic_configs:
            normalized = normalize_config(config)
            is_valid, errors = validate_config(normalized)
            assert is_valid is True, f"Normalized configuration validation failed: {errors}"


class TestConfigValidation:
    """Test configuration validation"""

    def test_validate_valid_config(self):
        """Test validate valid configuration"""
        config = {"server": {"name": "test-server", "instructions": "Test instructions"}}

        # Valid configuration should return (True, [])
        is_valid, errors = validate_config(config)
        assert is_valid is True
        assert errors == []

    def test_validate_invalid_config_missing_required(self):
        """Test validate configuration missing required fields"""
        config = {
            "server": {
                # Missing required name field
                "instructions": "Test instructions"
            }
        }

        # Invalid configuration should return (False, errors)
        is_valid, errors = validate_config(config)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_invalid_config_wrong_type(self):
        """Test validate configuration with wrong type"""
        config = {
            "server": {
                "name": 123,  # Should be string
                "instructions": "Test instructions",
            }
        }

        # Wrong type configuration should return (False, errors)
        is_valid, errors = validate_config(config)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_config_file(self):
        """Test validate configuration file"""
        config = {"server": {"name": "test-server", "instructions": "Test instructions"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            is_valid, loaded_config, errors = validate_config_file(config_path)
            assert is_valid is True
            assert loaded_config == config
            assert errors == []
        finally:
            Path(config_path).unlink()


class TestConfigMerging:
    """Test configuration merging"""

    def test_merge_configs_basic(self):
        """Test basic configuration merging"""
        base_config = {"server": {"name": "base-server", "instructions": "Base instructions", "port": 8080}}

        override_config = {"server": {"name": "override-server", "host": "localhost"}}

        merged = merge_configs(base_config, override_config)

        assert merged["server"]["name"] == "override-server"  # Overridden
        assert merged["server"]["instructions"] == "Base instructions"  # Preserved
        assert merged["server"]["port"] == 8080  # Preserved
        assert merged["server"]["host"] == "localhost"  # Added

    def test_merge_configs_deep_merge(self):
        """Test deep merging"""
        base_config = {"server": {"name": "test", "options": {"debug": True, "timeout": 30}}}

        override_config = {"server": {"options": {"debug": False, "retries": 3}}}

        merged = merge_configs(base_config, override_config)

        assert merged["server"]["name"] == "test"
        assert merged["server"]["options"]["debug"] is False  # Overridden
        assert merged["server"]["options"]["timeout"] == 30  # Preserved
        assert merged["server"]["options"]["retries"] == 3  # Added

    def test_merge_multiple_configs(self):
        """Test sequential merging of multiple configurations"""
        config1 = {"server": {"name": "server1", "port": 8080}}
        config2 = {"server": {"name": "server2", "host": "localhost"}}
        config3 = {"server": {"name": "server3", "debug": True}}

        # Sequential merging (merge_configs only accepts two parameters)
        merged = merge_configs(config1, config2)
        merged = merge_configs(merged, config3)

        assert merged["server"]["name"] == "server3"  # Last one takes effect
        assert merged["server"]["port"] == 8080
        assert merged["server"]["host"] == "localhost"
        assert merged["server"]["debug"] is True


class TestConfigFileOperations:
    """Test configuration file operations"""

    def test_detect_config_format_yaml(self):
        """Test detecting YAML format"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            config_path = f.name

        try:
            format_type = detect_config_format(config_path)
            assert format_type == "yaml"
        finally:
            Path(config_path).unlink()

    def test_detect_config_format_json(self):
        """Test detecting JSON format"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_path = f.name

        try:
            format_type = detect_config_format(config_path)
            assert format_type == "json"
        finally:
            Path(config_path).unlink()

    def test_load_yaml_config_file(self):
        """Test loading YAML configuration file"""
        config = {"server": {"name": "yaml-server", "instructions": "YAML test server"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            loaded_config = load_config_file(config_path)
            assert loaded_config == config
        finally:
            Path(config_path).unlink()

    def test_load_json_config_file(self):
        """Test loading JSON configuration file"""
        config = {"server": {"name": "json-server", "instructions": "JSON test server"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            loaded_config = load_config_file(config_path)
            assert loaded_config == config
        finally:
            Path(config_path).unlink()

    def test_save_yaml_config_file(self):
        """Test saving YAML configuration file"""
        config = {"server": {"name": "save-test", "instructions": "Save test server"}}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            config_path = f.name

        try:
            save_config_file(config, config_path)

            # Verify file was saved correctly
            loaded_config = load_config_file(config_path)
            assert loaded_config == config
        finally:
            Path(config_path).unlink()

    def test_save_json_config_file(self):
        """Test saving JSON configuration file"""
        config = {"server": {"name": "save-test", "instructions": "Save test server"}}

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_path = f.name

        try:
            save_config_file(config, config_path)

            # Verify file was saved correctly
            loaded_config = load_config_file(config_path)
            assert loaded_config == config
        finally:
            Path(config_path).unlink()


class TestConfigUpdate:
    """Test configuration update"""

    def test_update_config_basic(self):
        """Test basic configuration update"""
        config = {"server": {"name": "original", "instructions": "Original instructions"}}

        updated_config = update_config(config, "server.name", "updated")

        assert updated_config["server"]["name"] == "updated"
        assert updated_config["server"]["instructions"] == "Original instructions"

    def test_update_config_nested(self):
        """Test nested configuration update"""
        config = {"server": {"name": "test", "options": {"debug": True, "timeout": 30}}}

        updated_config = update_config(config, "server.options.debug", False)

        assert updated_config["server"]["name"] == "test"
        assert updated_config["server"]["options"]["debug"] is False
        assert updated_config["server"]["options"]["timeout"] == 30


class TestConfigSchema:
    """Test configuration schema"""

    def test_server_config_schema_exists(self):
        """Test server configuration schema exists"""
        assert SERVER_CONFIG_SCHEMA is not None
        assert isinstance(SERVER_CONFIG_SCHEMA, dict)

    def test_schema_has_required_fields(self):
        """Test schema contains required fields"""
        # Adjust test here based on actual schema structure
        assert "type" in SERVER_CONFIG_SCHEMA or "properties" in SERVER_CONFIG_SCHEMA


class TestErrorHandling:
    """Test error handling"""

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file"""
        from mcp_factory.exceptions import ConfigurationError
        with pytest.raises(ConfigurationError):
            load_config_file("/nonexistent/path/config.yaml")

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name

        try:
            from mcp_factory.exceptions import MCPFactoryError
            with pytest.raises(MCPFactoryError):
                load_config_file(config_path)
        finally:
            Path(config_path).unlink()

    def test_load_invalid_json(self):
        """Test loading invalid JSON file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json content}')
            config_path = f.name

        try:
            from mcp_factory.exceptions import MCPFactoryError
            with pytest.raises(MCPFactoryError):
                load_config_file(config_path)
        finally:
            Path(config_path).unlink()

    def test_merge_invalid_configs(self):
        """Test merging invalid configuration"""
        # Test error handling when merging with non-dictionary types
        with pytest.raises((TypeError, AttributeError)):
            merge_configs("invalid", {"valid": "config"})


class TestAdvancedFileOperations:
    """Test advanced file operations functionality"""

    def test_load_config_file_with_permission_error(self):
        """Test file permission error handling"""
        # Create a temporary file, then remove read permissions
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"server": {"name": "test"}}, f)
            config_path = f.name

        try:
            # Remove read permissions (only valid on Unix systems)
            import os
            import stat

            os.chmod(config_path, stat.S_IWRITE)

            from mcp_factory.exceptions import MCPFactoryError
            with pytest.raises(MCPFactoryError, match="file_permissions failed"):
                load_config_file(config_path)
        except (OSError, PermissionError):
            # May not be able to set permissions on some systems, skip this test
            pytest.skip("Cannot test permission error")
        finally:
            try:
                os.chmod(config_path, stat.S_IREAD | stat.S_IWRITE)
                Path(config_path).unlink()
            except (OSError, FileNotFoundError):
                pass

    def test_load_config_file_with_unicode_error(self):
        """Test file encoding error handling"""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".yaml", delete=False) as f:
            # Write invalid UTF-8 byte sequence
            f.write(b"\xff\xfe\x00\x00invalid utf-8")
            config_path = f.name

        try:
            from mcp_factory.exceptions import MCPFactoryError
            with pytest.raises(MCPFactoryError, match="read_file_encoding failed"):
                load_config_file(config_path)
        finally:
            Path(config_path).unlink()

    def test_load_config_with_auto_format_detection(self):
        """Test automatic format detection loading"""
        # Test automatic detection of files without extension
        with tempfile.NamedTemporaryFile(mode="w", suffix="", delete=False) as f:
            # Write YAML format but without extension
            yaml.dump({"server": {"name": "auto-detect"}}, f)
            config_path = f.name

        try:
            config = load_config_file(config_path)
            assert config["server"]["name"] == "auto-detect"
        finally:
            Path(config_path).unlink()

    def test_load_config_with_mixed_format_fallback(self):
        """Test format fallback mechanism"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # Write JSON format but use YAML extension
            json.dump({"server": {"name": "json-in-yaml"}}, f)
            config_path = f.name

        try:
            config = load_config_file(config_path)
            assert config["server"]["name"] == "json-in-yaml"
        finally:
            Path(config_path).unlink()

    def test_load_config_completely_unrecognizable_format(self):
        """Test completely unrecognizable format"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is not JSON or YAML format at all!")
            config_path = f.name

        try:
            from mcp_factory.exceptions import ConfigurationError
            with pytest.raises(ConfigurationError, match="Configuration file format error, must be object type"):
                load_config_file(config_path)
        finally:
            Path(config_path).unlink()

    def test_load_config_file_wrong_type_result(self):
        """Test loading result type error"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # YAML can be parsed as string rather than dictionary
            f.write("just a string, not an object")
            config_path = f.name

        try:
            from mcp_factory.exceptions import ConfigurationError
            with pytest.raises(ConfigurationError, match="Configuration file format error, must be object type"):
                load_config_file(config_path)
        finally:
            Path(config_path).unlink()


class TestStringConfigLoading:
    """Test loading configuration from string"""

    def test_load_config_from_string_yaml(self):
        """Test loading configuration from YAML string"""
        yaml_content = """
        server:
          name: string-test
          instructions: Test from string
        """

        config = load_config_from_string(yaml_content, "yaml")
        assert config["server"]["name"] == "string-test"

    def test_load_config_from_string_json(self):
        """Test loading configuration from JSON string"""
        json_content = '{"server": {"name": "json-string-test"}}'

        config = load_config_from_string(json_content, "json")
        assert config["server"]["name"] == "json-string-test"

    def test_load_config_from_string_invalid_yaml(self):
        """Test loading configuration from invalid YAML string"""
        invalid_yaml = """
        invalid: yaml: format:
          - badly
          structured
        """

        with pytest.raises(ConfigurationError, match="Configuration string parsing failed"):
            load_config_from_string(invalid_yaml, "yaml")

    def test_load_config_from_string_invalid_json(self):
        """Test loading configuration from invalid JSON string"""
        invalid_json = '{"invalid": json, "format": true,}'

        with pytest.raises(ConfigurationError, match="Configuration string parsing failed"):
            load_config_from_string(invalid_json, "json")

    def test_load_config_from_string_empty_yaml(self):
        """Test loading configuration from empty YAML string"""
        empty_yaml = ""

        config = load_config_from_string(empty_yaml, "yaml")
        assert config == {}


class TestFormatDetection:
    """Test format detection functionality"""

    def test_detect_config_format_yaml_extensions(self):
        """Test YAML extension detection"""
        assert detect_config_format("config.yaml") == "yaml"
        assert detect_config_format("config.yml") == "yaml"

    def test_detect_config_format_json_extension(self):
        """Test JSON extension detection"""
        assert detect_config_format("config.json") == "json"

    def test_detect_config_format_unknown_extension(self):
        """Test content detection of unknown extensions"""
        # Test JSON content detection
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write('{"key": "value"}')
            config_path = f.name

        try:
            assert detect_config_format(config_path) == "json"
        finally:
            Path(config_path).unlink()

        # Test JSON array content detection
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write('[{"key": "value"}]')
            config_path = f.name

        try:
            assert detect_config_format(config_path) == "json"
        finally:
            Path(config_path).unlink()

    def test_detect_config_format_read_error_fallback(self):
        """Test fallback behavior when read error occurs"""
        # Use nonexistent file path
        assert detect_config_format("/nonexistent/file.conf") == "yaml"


class TestConfigSaving:
    """Test configuration saving functionality"""

    def test_save_config_file_auto_format(self):
        """Test automatic format saving"""
        config = {"server": {"name": "auto-save"}}

        # Test YAML format automatic saving
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            yaml_path = f.name

        try:
            save_config_file(config, yaml_path, "auto")
            loaded = load_config_file(yaml_path)
            assert loaded == config
        finally:
            Path(yaml_path).unlink()

    def test_save_config_file_with_parent_dir_creation(self):
        """Test automatic parent directory creation when saving"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "nested" / "deep" / "config.yaml"
            config = {"server": {"name": "nested-save"}}

            save_config_file(config, nested_path)

            assert nested_path.exists()
            loaded = load_config_file(nested_path)
            assert loaded == config

        # Test JSON format automatic saving
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name

        try:
            save_config_file(config, json_path, "auto")
            loaded = load_config_file(json_path)
            assert loaded == config
        finally:
            Path(json_path).unlink()

    def test_save_config_file_auto_format_fallback(self):
        """Test fallback behavior for automatic format saving"""
        config = {"server": {"name": "test"}}

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            xml_path = f.name

        try:
            # In auto mode, will fallback to YAML format
            save_config_file(config, xml_path, "auto")

            # Verify file can be loaded
            loaded = load_config_file(xml_path)
            assert loaded == config
        finally:
            Path(xml_path).unlink()

    def test_save_config_file_with_write_error(self):
        """Test write error when saving"""
        config = {"server": {"name": "test"}}

        # Use mock to mock write error
        from unittest.mock import mock_open, patch

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            config_path = f.name

        try:
            # Mock open function to throw exception
            with patch("builtins.open", mock_open()) as mock_file:
                mock_file.side_effect = OSError("Mock write error")

                with pytest.raises(ConfigurationError, match="Configuration file save failed"):
                    save_config_file(config, config_path)
        finally:
            Path(config_path).unlink()


class TestConfigValidationEdgeCases:
    """Test configuration validation edge cases"""

    def test_validate_empty_config(self):
        """Test validating empty configuration"""
        is_valid, errors = validate_config({})
        assert is_valid is False
        assert "Configuration is empty" in errors

    def test_validate_config_file_with_normalization_error(self):
        """Test configuration file validation with normalization error"""
        # Create a configuration that would cause normalization failure
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # Mock situation that could cause normalization failure
            yaml.dump({"server": None}, f)  # None value might cause issues
            config_path = f.name

        try:
            # Use patch to mock normalization failure
            from unittest.mock import patch

            with patch("mcp_factory.config.manager.normalize_config", side_effect=Exception("normalization failure")):
                is_valid, config, errors = validate_config_file(config_path)
                assert is_valid is False
                assert any("Configuration normalization failed" in error for error in errors)
        finally:
            Path(config_path).unlink()


class TestConfigUpdateAdvanced:
    """Test advanced configuration update functionality"""

    def test_update_config_create_nested_path(self):
        """Test updating configuration when creating nested paths"""
        config = {"server": {"name": "test"}}

        updated = update_config(config, "new.nested.key", "value")

        assert updated["new"]["nested"]["key"] == "value"
        assert updated["server"]["name"] == "test"  # Original fields remain unchanged

    def test_update_config_override_existing(self):
        """Test updating configuration when overriding existing values"""
        config = {"server": {"name": "old-name", "port": 8080}}

        updated = update_config(config, "server.name", "new-name")

        assert updated["server"]["name"] == "new-name"
        assert updated["server"]["port"] == 8080  # Other fields remain unchanged

    def test_update_config_deep_nested_creation(self):
        """Test deep nested path creation"""
        config = {}

        updated = update_config(config, "a.b.c.d.e.f", "deep-value")

        assert updated["a"]["b"]["c"]["d"]["e"]["f"] == "deep-value"


class TestConfigFileValidationEdgeCases:
    """Test configuration file validation edge cases"""

    def test_load_config_file_not_a_file(self):
        """Test loading configuration from non-file path (such as directory)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a directory instead of a file
            dir_path = Path(temp_dir) / "config_directory"
            dir_path.mkdir()

            from mcp_factory.exceptions import ConfigurationError
            with pytest.raises(ConfigurationError) as exc_info:
                load_config_file(str(dir_path))
            assert "Path is not a file" in str(exc_info.value)

    def test_load_config_file_auto_format_detection_failure(self):
        """Test automatic format detection failure situation"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            # Write content that is neither valid YAML nor valid JSON
            f.write("invalid:\n  - unclosed: [\n  - another: }")  # Invalid YAML and JSON
            config_path = f.name

        try:
            from mcp_factory.exceptions import ConfigurationError
            with pytest.raises(ConfigurationError) as exc_info:
                load_config_file(config_path)
            assert "Cannot recognize configuration file format" in str(exc_info.value)
        finally:
            Path(config_path).unlink()

    def test_load_config_file_mixed_format_yaml_first_success(self):
        """Test mixed format file, YAML parsing success"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            # Write valid YAML content
            f.write("server:\n  name: test-server\n  instructions: test")
            config_path = f.name

        try:
            config = load_config_file(config_path)
            assert config["server"]["name"] == "test-server"
        finally:
            Path(config_path).unlink()

    def test_load_config_file_mixed_format_yaml_fail_json_success(self):
        """Test mixed format file, YAML failure but JSON success"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            # Write valid JSON but invalid YAML content
            f.write('{"server": {"name": "test-server", "instructions": "test"}}')
            config_path = f.name

        try:
            config = load_config_file(config_path)
            assert config["server"]["name"] == "test-server"
        finally:
            Path(config_path).unlink()

    def test_load_config_file_wrong_result_type(self):
        """Test configuration file content is not dictionary type"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # Write array instead of object
            f.write("- item1\n- item2\n- item3")
            config_path = f.name

        try:
            from mcp_factory.exceptions import ConfigurationError
            with pytest.raises(ConfigurationError) as exc_info:
                load_config_file(config_path)
            assert "Configuration file format error, must be object type" in str(exc_info.value)
        finally:
            Path(config_path).unlink()


class TestConfigFormatDetectionAdvanced:
    """Test advanced configuration format detection functionality"""

    def test_detect_config_format_content_based_object(self):
        """Test content-based format detection (object)"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write('{"key": "value"}')
            config_path = f.name

        try:
            format_type = detect_config_format(config_path)
            assert format_type == "json"
        finally:
            Path(config_path).unlink()

    def test_detect_config_format_content_based_array(self):
        """Test content-based format detection (array)"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write('[{"key": "value"}]')
            config_path = f.name

        try:
            format_type = detect_config_format(config_path)
            assert format_type == "json"
        finally:
            Path(config_path).unlink()

    def test_detect_config_format_content_based_yaml_fallback(self):
        """Test content-based format detection (YAML fallback)"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write("key: value\nanother: setting")
            config_path = f.name

        try:
            format_type = detect_config_format(config_path)
            assert format_type == "yaml"
        finally:
            Path(config_path).unlink()

    def test_detect_config_format_read_error_fallback(self):
        """Test fallback behavior when read error occurs"""
        # Use nonexistent file path
        nonexistent_path = "/nonexistent/path/config.conf"
        format_type = detect_config_format(nonexistent_path)
        assert format_type == "yaml"  # Should return default yaml


class TestConfigFileExceptionHandling:
    """Test configuration file various exception handling"""

    def test_load_config_file_os_error_simulation(self):
        """Test mock OS error exception"""
        # Create a file then delete it, mock OSError when reading
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=True) as f:
            f.write("server:\n  name: test")
            f.flush()
            config_path = f.name
            # File is deleted here

        # Now try to read the deleted file
        from mcp_factory.exceptions import ConfigurationError
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_file(config_path)
        assert "Configuration file does not exist" in str(exc_info.value)

    def test_load_config_file_unicode_decode_error_simulation(self):
        """Test mock Unicode decode error"""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".yaml", delete=False) as f:
            # Write invalid UTF-8 byte sequence
            f.write(b"\xff\xfe\x00\x00invalid utf-8")
            config_path = f.name

        try:
            from mcp_factory.exceptions import MCPFactoryError
            with pytest.raises(MCPFactoryError) as exc_info:
                load_config_file(config_path)
            assert "read_file_encoding failed" in str(exc_info.value)
        finally:
            Path(config_path).unlink()


class TestConfigNormalizationAdvanced:
    """Test advanced configuration normalization scenarios"""

    def test_normalize_config_deep_copy_isolation(self):
        """Test normalization does not affect original configuration"""
        original_config = {"server": {"instructions": "original"}, "nested": {"value": "test"}}

        normalized = normalize_config(original_config)

        # Modify normalized configuration
        normalized["server"]["name"] = "normalized-server"
        normalized["nested"]["value"] = "modified"

        # Original configuration should not be affected
        assert "name" not in original_config["server"]
        assert original_config["nested"]["value"] == "test"

    def test_normalize_config_server_without_name_existing_fields(self):
        """Test normalization when server field exists but missing name"""
        config = {"server": {"instructions": "test instructions", "host": "localhost", "port": 8080}}

        normalized = normalize_config(config)

        assert normalized["server"]["name"] == "unnamed-server"
        assert normalized["server"]["instructions"] == "test instructions"
        assert normalized["server"]["host"] == "localhost"
        assert normalized["server"]["port"] == 8080


class TestConfigValidationErrorDetails:
    """Test configuration validation error details"""

    def test_validate_config_schema_error_path_reporting(self):
        """Test schema validation error path reporting"""
        config = {
            "server": {
                "name": "test",
                "instructions": 123,  # Should be string
            }
        }

        is_valid, errors = validate_config(config)
        assert is_valid is False
        assert len(errors) > 0
        # Check error message contains path information
        error_message = errors[0]
        assert "Validation error" in error_message

    def test_validate_config_empty_server_name(self):
        """Test empty server name validation"""
        # Test empty string name
        config1 = {"server": {"name": ""}}
        is_valid, errors = validate_config(config1)
        assert is_valid is False
        assert any("Server name is required" in error for error in errors)

        # Test None name
        config2 = {"server": {"name": None}}
        is_valid, errors = validate_config(config2)
        assert is_valid is False
        assert any("Validation error" in error for error in errors)  # Schema validation error

        # Test missing name field
        config3 = {"server": {}}
        is_valid, errors = validate_config(config3)
        assert is_valid is False
        assert any("Validation error" in error and "name" in error for error in errors)  # Schema validation error


class TestConfigFileValidationIntegration:
    """Test configuration file validation integration scenarios"""

    def test_validate_config_file_normalization_error_simulation(self):
        """Test mock of configuration file normalization error"""
        # Create a configuration file that would cause normalization error
        config = {"server": {"name": "test"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            # Mock exception during normalization process
            import unittest.mock

            with unittest.mock.patch(
                "mcp_factory.config.manager.normalize_config", side_effect=Exception("mock normalization error")
            ):
                is_valid, loaded_config, errors = validate_config_file(config_path)

                assert is_valid is False
                assert "Configuration normalization failed" in str(errors[0])
                assert loaded_config == config  # Should return original configuration
        finally:
            Path(config_path).unlink()
