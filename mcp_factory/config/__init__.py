"""Configuration management module

Focused on configuration file loading, validation and schema definition
"""

from .manager import (
    detect_config_format,
    # Configuration generation and saving
    get_default_config,
    # File loading
    load_config_file,
    load_config_from_string,
    # Configuration operations
    merge_configs,
    # Configuration validation and normalization
    normalize_config,
    save_config_file,
    update_config,
    validate_config,
    validate_config_file,
    # External server configuration validation
    validate_external_servers_config,
)
from .schema import SERVER_CONFIG_SCHEMA

# Backward compatibility alias
load_config = load_config_file

__all__ = [
    # Schema definition
    "SERVER_CONFIG_SCHEMA",
    "detect_config_format",
    # Default configuration
    "get_default_config",
    "load_config",  # Backward compatibility alias
    # File loading
    "load_config_file",
    "load_config_from_string",
    # Configuration operations
    "merge_configs",
    # Configuration validation and normalization
    "normalize_config",
    # Configuration saving
    "save_config_file",
    "update_config",
    "validate_config",
    "validate_config_file",
    # External server configuration validation
    "validate_external_servers_config",
]

__version__ = "1.3.0"

__status__ = "refactoring"
