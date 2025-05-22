"""Configuration File Validation Module

Module for validating the format and content of FastMCP server configuration files.
"""

import os
from typing import Any, Dict, List, Tuple

import jsonschema
import yaml

#######################
# Configuration File Schema Definition
#######################

# Define JSON Schema for configuration file
SERVER_CONFIG_SCHEMA = {
    "type": "object",
    "required": ["server"],
    "properties": {
        "server": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Server name, used to identify this MCP server instance",
                },
                "instructions": {
                    "type": "string",
                    "description": "Server instructions, providing guidance to clients on how to use this server",
                },
                "host": {
                    "type": "string",
                    "description": "HTTP server listening address, use 0.0.0.0 to listen on all network interfaces",
                    "default": "127.0.0.1",
                },
                "port": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 65535,
                    "description": "HTTP server listening port",
                    "default": 8000,
                },
                "transport": {
                    "type": "string",
                    "enum": ["stdio", "sse", "streamable-http"],
                    "description": "Server transport protocol: stdio (standard input/output), "
                    "sse (server-sent events), "
                    "streamable-http (HTTP streaming)",
                    "default": "streamable-http",
                },
                "debug": {
                    "type": "boolean",
                    "description": "Whether to enable debug mode, which outputs more detailed log information",
                    "default": False,
                },
            },
        },
        "auth": {
            "type": "object",
            "properties": {
                # New structure: Reference to created provider
                "provider_id": {
                    "type": "string",
                    "description": "Authentication provider ID, reference to a created authentication provider",
                },
                # Authentication policies
                "policies": {
                    "type": "object",
                    "properties": {
                        "admin_users": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of administrator users who will have access to all management tools",
                        },
                        "token_whitelist": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of whitelisted tokens allowed to access without full authentication",
                        },
                    },
                },
            },
        },
        "tools": {
            "type": "object",
            "properties": {
                "expose_management_tools": {
                    "type": "boolean",
                    "description": "Whether to automatically register FastMCP methods as management tools",
                    "default": True,
                },
                "enabled_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of enabled tools, if empty all tools are enabled",
                },
                "tool_permissions": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "description": "Permission configuration for each tool",
                        "properties": {
                            "requiresAuth": {
                                "type": "boolean",
                                "description": "Whether authentication is required to use this tool",
                            },
                            "adminOnly": {
                                "type": "boolean",
                                "description": "Whether only administrators can use this tool",
                            },
                            "destructiveHint": {
                                "type": "boolean",
                                "description": "Whether the tool has a hint for potentially destructive operations",
                            },
                        },
                    },
                    "description": "Tool permission configuration, keys are tool names, values are permission configurations",
                },
            },
        },
        "advanced": {
            "type": "object",
            "description": "Advanced parameters section, supports any FastMCP native parameters",
            "additionalProperties": True,
            "properties": {
                "log_level": {
                    "type": "string",
                    "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    "description": "Log level, controls the detail level of log output",
                    "default": "INFO",
                },
                "cache_expiration_seconds": {
                    "type": "number",
                    "description": "Cache expiration time (seconds), used to control internal cache lifetime",
                    "default": 0,
                },
                "on_duplicate_tools": {
                    "type": "string",
                    "enum": ["warn", "error", "replace", "ignore"],
                    "description": "Strategy for handling duplicate tools",
                    "default": "warn",
                },
                "on_duplicate_resources": {
                    "type": "string",
                    "enum": ["warn", "error", "replace", "ignore"],
                    "description": "Strategy for handling duplicate resources",
                    "default": "warn",
                },
                "on_duplicate_prompts": {
                    "type": "string",
                    "enum": ["warn", "error", "replace", "ignore"],
                    "description": "Strategy for handling duplicate prompts",
                    "default": "warn",
                },
                "sse_path": {
                    "type": "string",
                    "description": "SSE endpoint path, only valid when transport is sse",
                    "default": "/sse",
                },
                "message_path": {
                    "type": "string",
                    "description": "Message endpoint path",
                    "default": "/messages/",
                },
                "streamable_http_path": {
                    "type": "string",
                    "description": "HTTP stream endpoint path, only valid when transport is streamable-http",
                    "default": "/mcp",
                },
                "json_response": {
                    "type": "boolean",
                    "description": "Whether to use JSON response format",
                    "default": False,
                },
                "stateless_http": {
                    "type": "boolean",
                    "description": "Whether to use stateless HTTP mode, creating a new transport for each request",
                    "default": False,
                },
                # FastMCP constructor parameters
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Server tag list, used to identify and categorize server instances",
                },
                "dependencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Server dependency list, used to specify dependencies required by the server",
                },
            },
        },
    },
}

#######################
# Configuration Loading and Validation Functions
#######################


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from file

    Args:
        config_path: Configuration file path

    Returns:
        Loaded configuration dictionary

    Raises:
        FileNotFoundError: Configuration file does not exist
        yaml.YAMLError: Configuration file format error
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file does not exist: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        try:
            config = yaml.safe_load(f)
            return config
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Configuration file format error: {str(e)}")


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate whether the configuration dictionary conforms to the expected schema

    Args:
        config: Configuration dictionary

    Returns:
        Validation result tuple (is_valid, errors)
        - is_valid: Whether the configuration is valid
        - errors: List of error messages
    """
    errors = []

    # Empty configuration check
    if not config:
        return False, ["Configuration is empty"]

    # JSON Schema validation
    try:
        jsonschema.validate(instance=config, schema=SERVER_CONFIG_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        path = ".".join(str(p) for p in e.path)
        message = e.message
        errors.append(f"Validation error({path}): {message}")
        return False, errors

    # Server name check (must be provided)
    server_config = config.get("server", {})
    if not server_config.get("name"):
        errors.append("Server name is required")
        return False, errors

    return True, []


def validate_config_file(config_path: str) -> Tuple[bool, Dict[str, Any], List[str]]:
    """Load and validate configuration file

    Args:
        config_path: Configuration file path

    Returns:
        Validation result tuple (is_valid, config, errors)
        - is_valid: Whether the configuration is valid
        - config: Loaded configuration dictionary (may be empty if loading fails)
        - errors: List of error messages
    """
    config = {}
    errors = []

    # Try to load configuration
    try:
        config = load_config(config_path)
    except FileNotFoundError as e:
        errors.append(str(e))
        return False, {}, errors
    except yaml.YAMLError as e:
        errors.append(str(e))
        return False, {}, errors

    # Validate configuration content
    is_valid, validation_errors = validate_config(config)
    if not is_valid:
        errors.extend(validation_errors)
        return False, config, errors

    return True, config, []


def get_default_config() -> Dict[str, Any]:
    """Get default configuration dictionary

    Returns:
        Default configuration dictionary with minimal required fields
    """
    return {
        "server": {
            "name": "default-mcp-server",
            "instructions": "Default MCP Server",
            "host": "127.0.0.1",
            "port": 8000,
            "transport": "streamable-http",
            "debug": False,
        },
        "tools": {
            "expose_management_tools": True,
            "enabled_tools": [],
        },
        "advanced": {
            "log_level": "INFO",
        },
    }
