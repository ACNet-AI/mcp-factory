"""Configuration Manager

Provides configuration file loading, validation and processing functionality
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from mcp_factory.exceptions import ConfigurationError, ErrorHandler

from .schema import SERVER_CONFIG_SCHEMA

logger = logging.getLogger(__name__)
error_handler = ErrorHandler("config.manager")


# ===============================
# Configuration File Loading Functions
# ===============================


def load_config_file(config_path: str | Path) -> dict[str, Any]:
    """Load configuration file

    Args:
        config_path: Configuration file path, supports YAML and JSON formats

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: File does not exist
        ValueError: File format error or parsing failed
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise ConfigurationError(f"Configuration file does not exist: {config_path}", config_path=str(config_path))

    if not config_path.is_file():
        raise ConfigurationError(f"Path is not a file: {config_path}", config_path=str(config_path))

    try:
        with open(config_path, encoding="utf-8") as f:
            content = f.read()

        # Determine format based on file extension
        suffix = config_path.suffix.lower()

        if suffix in [".yaml", ".yml"]:
            config = yaml.safe_load(content)
        elif suffix == ".json":
            config = json.loads(content)
        else:
            # Try auto-detection, prioritize YAML
            try:
                config = yaml.safe_load(content)
            except yaml.YAMLError:
                try:
                    config = json.loads(content)
                except json.JSONDecodeError:
                    raise ConfigurationError(
                        f"Cannot recognize configuration file format: {config_path}", config_path=str(config_path)
                    ) from None

        if not isinstance(config, dict):
            raise ConfigurationError(
                f"Configuration file format error, must be object type: {config_path}", config_path=str(config_path)
            )

        logger.info("Successfully loaded configuration file: %s", config_path)
        return config

    except yaml.YAMLError as e:
        error_handler.handle_error("parse_yaml", e, {"config_path": str(config_path)})
        raise  # This line will never be reached due to error_handler.handle_error raising
    except json.JSONDecodeError as e:
        error_handler.handle_error("parse_json", e, {"config_path": str(config_path)})
        raise  # This line will never be reached due to error_handler.handle_error raising
    except UnicodeDecodeError as e:
        error_handler.handle_error("read_file_encoding", e, {"config_path": str(config_path)})
        raise  # This line will never be reached due to error_handler.handle_error raising
    except PermissionError as e:
        error_handler.handle_error("file_permissions", e, {"config_path": str(config_path)})
        raise  # This line will never be reached due to error_handler.handle_error raising
    except OSError as e:
        error_handler.handle_error("file_system", e, {"config_path": str(config_path)})
        raise  # This line will never be reached due to error_handler.handle_error raising
    except Exception as e:
        error_handler.handle_error("load_config_file", e, {"config_path": str(config_path)})
        raise  # This line will never be reached due to error_handler.handle_error raising


def load_config_from_string(content: str, format_hint: str = "yaml") -> dict[str, Any]:
    """Parse configuration from string

    Args:
        content: Configuration string content
        format_hint: Format hint: "yaml" or "json"

    Returns:
        Configuration dictionary

    Raises:
        ConfigurationError: Parsing failed
    """
    try:
        if format_hint == "json":
            result = json.loads(content)
            return result if isinstance(result, dict) else {}

        # Default to YAML
        result = yaml.safe_load(content)
        return result if isinstance(result, dict) else {}
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ConfigurationError(f"Configuration string parsing failed: {e}") from e


def detect_config_format(config_path: str | Path) -> str:
    """Intelligently detect configuration file format

    Args:
        config_path: Configuration file path

    Returns:
        Detected format: "yaml" or "json"
    """
    config_path = Path(config_path)

    # First judge by extension
    suffix = config_path.suffix.lower()
    if suffix in [".yaml", ".yml"]:
        return "yaml"
    if suffix == ".json":
        return "json"

    # If extension is unclear, read content to judge
    try:
        with open(config_path, encoding="utf-8") as f:
            content = f.read().strip()

        if (content.startswith("{") and content.endswith("}")) or (content.startswith("[") and content.endswith("]")):
            return "json"
        return "yaml"  # Default YAML
    except Exception:
        return "yaml"  # Default YAML on error


# ===============================
# Configuration Validation and Normalization Functions
# ===============================


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize configuration, fill default values and infer missing fields

    Args:
        config: Original configuration dictionary

    Returns:
        Normalized configuration dictionary
    """
    import copy

    normalized = copy.deepcopy(config)

    # Ensure basic structure exists
    if "server" not in normalized:
        normalized["server"] = {}

    # Handle top-level name field, move to server.name
    if "name" in normalized and "name" not in normalized["server"]:
        normalized["server"]["name"] = normalized.pop("name")

    # Set default value for server.name (if missing)
    if "name" not in normalized["server"]:
        normalized["server"]["name"] = "unnamed-server"

    # Normalize external server configuration
    if "mcpServers" in normalized:
        _normalize_external_servers(normalized["mcpServers"])

    return normalized


def _normalize_external_servers(external_config: dict[str, Any]) -> None:
    """Normalize mcpServers configuration, auto-infer transport and other fields"""
    # mcpServers structure directly contains server configurations
    for server_config in external_config.values():
        # Auto-infer transport type
        if "transport" not in server_config:
            if "command" in server_config:
                # Local script server defaults to stdio
                server_config["transport"] = "stdio"
            elif "url" in server_config:
                # Remote server inferred from URL
                url = server_config["url"]
                if "/sse" in url or url.endswith("/sse"):
                    server_config["transport"] = "sse"
                else:
                    server_config["transport"] = "streamable-http"

        # Set default environment variables for local servers
        if "command" in server_config and "env" not in server_config:
            server_config["env"] = {}

        # Set default timeout for remote servers
        if "url" in server_config and "timeout" not in server_config:
            server_config["timeout"] = 30


def validate_config(config: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate if configuration dictionary conforms to expected schema

    Args:
        config: Configuration dictionary

    Returns:
        Validation result tuple (is_valid, errors)
        - is_valid: Whether configuration is valid
        - errors: List of error messages
    """
    errors = []

    # Empty configuration check
    if not config:
        return False, ["Configuration is empty"]

    # JSON Schema validation
    try:
        jsonschema.validate(instance=config, schema=SERVER_CONFIG_SCHEMA)
        logger.debug("Configuration validation passed")
    except jsonschema.exceptions.ValidationError as e:
        path = ".".join(str(p) for p in e.path)
        message = e.message
        errors.append(f"Validation error ({path}): {message}")
        return False, errors

    # Server name check (required)
    server_config = config.get("server", {})
    if not server_config.get("name"):
        errors.append("Server name is required")
        return False, errors

    return True, []


def validate_config_file(config_path: str) -> tuple[bool, dict[str, Any], list[str]]:
    """Load, normalize and validate configuration file

    Args:
        config_path: Configuration file path

    Returns:
        Validation result tuple (is_valid, normalized_config, errors)
        - is_valid: Whether configuration is valid
        - normalized_config: Normalized configuration dictionary (may be empty if loading fails)
        - errors: List of error messages
    """
    config = {}
    errors = []

    # Try to load configuration
    try:
        config = load_config_file(config_path)
    except (FileNotFoundError, ValueError) as e:
        errors.append(str(e))
        return False, {}, errors

    # Normalize configuration
    try:
        normalized_config = normalize_config(config)
    except Exception as e:
        errors.append(f"Configuration normalization failed: {e}")
        return False, config, errors

    # Validate normalized configuration
    is_valid, validation_errors = validate_config(normalized_config)
    if not is_valid:
        errors.extend(validation_errors)
        return False, normalized_config, errors

    return True, normalized_config, []


def validate_external_servers_config(config: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate completeness and security of mcpServers configuration

    Args:
        config: Complete configuration dictionary

    Returns:
        tuple: (is_valid, error_messages)
    """
    errors = []

    if "mcpServers" not in config:
        return True, []  # No external server configuration is valid

    external_servers = config["mcpServers"]

    # 1. Check server count limit
    max_servers = 20  # Default limit
    if len(external_servers) > max_servers:
        errors.append(f"External server count ({len(external_servers)}) exceeds limit ({max_servers})")

    # 2. Basic configuration validation
    for server_name, server_config in external_servers.items():
        # Check required fields
        if not server_config.get("command") and not server_config.get("url"):
            errors.append(f"Server '{server_name}' must specify command or url")

        # Check URL format
        if "url" in server_config:
            url = server_config["url"]
            if not url.startswith(("http://", "https://")):
                errors.append(f"Server '{server_name}' has invalid URL format: {url}")

    return len(errors) == 0, errors


def _has_dependency_cycle(dependencies_map: dict[str, Any]) -> bool:
    """Detect cycles in dependency relationships"""
    visited = set()
    rec_stack = set()

    def dfs(node: str) -> bool:
        if node in rec_stack:
            return True  # Cycle detected
        if node in visited:
            return False

        visited.add(node)
        rec_stack.add(node)

        for neighbor in dependencies_map.get(node, []):
            if neighbor in dependencies_map and dfs(neighbor):
                return True

        rec_stack.remove(node)
        return False

    return any(node not in visited and dfs(node) for node in dependencies_map)


# ===============================
# Configuration Generation and Saving Functions
# ===============================


def get_default_config() -> dict[str, Any]:
    """Get default configuration dictionary

    Returns:
        Default configuration dictionary containing minimum required fields
    """
    return {
        "server": {
            "name": "Default Server",
            "instructions": "This is a default MCP server",
        },
        "transport": {"transport": "stdio", "host": "127.0.0.1", "port": 8000, "log_level": "INFO"},
        "management": {"expose_management_tools": True},
        "components": {
            "tools": [],
            "resources": [],
            "prompts": [],
            "auto_discovery": {
                "enabled": True,
                "scan_directories": ["tools", "resources", "prompts"],
                "ignore_patterns": ["__pycache__", "*.pyc", "__init__.py"],
            },
        },
        "middleware": [],
        "auth": {"provider": "none"},
        "mcpServers": {},
    }


def save_config_file(config: dict[str, Any], config_path: str | Path, format_hint: str = "auto") -> None:
    """Save configuration to file

    Args:
        config: Configuration dictionary
        config_path: Save path
        format_hint: Format hint, "yaml", "json" or "auto" (automatically determine by extension)

    Raises:
        ConfigurationError: Format not supported or save failed
    """
    config_path = Path(config_path)

    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine save format
    if format_hint == "auto":
        suffix = config_path.suffix.lower()
        if suffix in [".yaml", ".yml"]:
            format_hint = "yaml"
        elif suffix == ".json":
            format_hint = "json"
        else:
            format_hint = "yaml"  # Default to YAML

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            if format_hint == "json":
                json.dump(config, f, indent=2, ensure_ascii=False)
            else:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except Exception as e:
        raise ConfigurationError(f"Configuration file save failed: {e}", config_path=str(config_path)) from e


# ===============================
# Configuration Operation Functions
# ===============================


def merge_configs(base_config: dict[str, Any], override_config: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two configuration dictionaries

    Args:
        base_config: Base configuration
        override_config: Override configuration

    Returns:
        Merged configuration dictionary
    """
    import copy

    result = copy.deepcopy(base_config)

    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                _deep_merge(base[key], value)
            else:
                base[key] = value

    _deep_merge(result, override_config)
    return result


def update_config(config: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """Update specific field in configuration

    Args:
        config: Configuration dictionary
        path: Field path, dot-separated (e.g.: "server.name")
        value: New value

    Returns:
        Updated configuration dictionary
    """
    import copy

    result = copy.deepcopy(config)
    parts = path.split(".")
    current = result

    # Navigate to target location
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set value
    current[parts[-1]] = value
    return result
