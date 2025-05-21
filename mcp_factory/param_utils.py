"""Parameter processing utility module.

This module provides parameter definitions and processing functions shared by
FastMCPFactory and ManagedServer.
"""

import logging
from typing import Any, Dict, List, Optional, Set

# Set up logging
logger = logging.getLogger(__name__)

#######################
# Parameter definitions and type mappings
#######################

# Parameter type definitions
CONSTRUCTION_PARAMS = {
    # Core construction parameters
    "name",
    "instructions",
    "lifespan",
    "tags",
    "dependencies",
    "tool_serializer",
}

SETTINGS_PARAMS = {
    # Original setting parameters
    "log_level",
    "on_duplicate_tools",
    "on_duplicate_resources",
    "on_duplicate_prompts",
    # Runtime configuration parameters
    "host",
    "port",
    "transport",
    "debug",
    # Advanced setting parameters
    "sse_path",
    "message_path",
    "streamable_http_path",
    "json_response",
    "stateless_http",
    "cache_expiration_seconds",
}

# Collection type parameters
COLLECTION_PARAMS = {"tags", "dependencies"}

# Parameter type mappings
PARAM_TYPES = {
    "name": str,
    "instructions": str,
    "host": str,
    "port": int,
    "transport": str,
    "tags": set,
    "dependencies": list,
    "log_level": str,
    "debug": bool,
    "json_response": bool,
    "stateless_http": bool,
    "cache_expiration_seconds": int,
}

#######################
# Parameter validation and extraction functions
#######################


def validate_param(name: str, value: Any) -> None:
    """Validate if parameter type is correct.

    Args:
        name: Parameter name
        value: Parameter value

    Raises:
        TypeError: If parameter type is incorrect
        ValueError: If parameter value is invalid
    """
    if name not in PARAM_TYPES or value is None:
        return

    expected_type = PARAM_TYPES[name]

    # Special handling for collection types
    if name == "tags" and not isinstance(value, set):
        if isinstance(value, (list, tuple)):
            return  # Allow lists/tuples to be converted to sets
        raise TypeError(
            f"Parameter '{name}' must be a set, list or tuple, got {type(value).__name__}"
        )

    # Standard type checking
    if not isinstance(value, expected_type):
        raise TypeError(
            f"Parameter '{name}' must be {expected_type.__name__}, got {type(value).__name__}"
        )

    # Value checking for specific parameters
    if name == "port" and (value < 0 or value > 65535):
        raise ValueError(f"Port must be between 0 and 65535, got {value}")

    if name == "log_level" and value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        logger.warning(f"Unexpected log level: {value}")


def extract_config_section(config: Optional[Dict[str, Any]], section: str) -> Dict[str, Any]:
    """Extract a specific section from configuration.

    Args:
        config: Configuration dictionary, may be None
        section: Section name, such as "server", "auth", "advanced"

    Returns:
        Extracted configuration section, or empty dictionary if it doesn't exist
    """
    if not config:
        return {}
    return config.get(section, {})


#######################
# Parameter merging and processing functions
#######################


def merge_tags(existing_tags: Optional[Set[str]], new_tags: Optional[Set[str]]) -> Set[str]:
    """Merge tag sets.

    Args:
        existing_tags: Existing tag set, may be None
        new_tags: New tag set, may be None

    Returns:
        Merged tag set
    """
    # Convert non-set types
    if new_tags and not isinstance(new_tags, set):
        if isinstance(new_tags, (list, tuple)):
            new_tags = set(new_tags)
        else:
            logger.warning(f"Invalid tags type: {type(new_tags).__name__}, expected set")
            new_tags = None

    if not existing_tags:
        return set(new_tags) if new_tags else set()

    if new_tags:
        existing_tags.update(new_tags)

    return existing_tags


def merge_dependencies(
    existing_deps: Optional[List[str]], new_deps: Optional[List[str]]
) -> List[str]:
    """Merge dependency lists, maintain order and avoid duplicates.

    Args:
        existing_deps: Existing dependency list, may be None
        new_deps: New dependency list, may be None

    Returns:
        Merged dependency list
    """
    # Convert non-list types
    if new_deps and not isinstance(new_deps, list):
        if isinstance(new_deps, (set, tuple)):
            new_deps = list(new_deps)
        else:
            logger.warning(f"Invalid dependencies type: {type(new_deps).__name__}, expected list")
            new_deps = None

    if not existing_deps:
        return list(new_deps) if new_deps else []

    if not new_deps:
        return existing_deps

    # Add new dependencies (avoiding duplicates)
    unique_new_deps = [d for d in new_deps if d not in existing_deps]
    if unique_new_deps:
        return existing_deps + unique_new_deps

    return existing_deps


def apply_advanced_params(
    instance: Any, advanced_config: Dict[str, Any], runtime_kwargs: Dict[str, Any]
) -> None:
    """Apply advanced parameters to an instance.

    Args:
        instance: Instance object to apply parameters to
        advanced_config: Advanced configuration dictionary
        runtime_kwargs: Runtime parameter dictionary, used to store non-direct attribute parameters
    """
    for key, value in advanced_config.items():
        # Skip empty values
        if value is None:
            continue

        # Validate parameter type
        try:
            validate_param(key, value)
        except (TypeError, ValueError) as e:
            logger.warning(f"Parameter validation failed: {e}")
            continue

        # Special handling for collection type parameters
        if key == "tags":
            # Merge tag sets
            if not hasattr(instance, "tags") or not instance.tags:
                instance.tags = set(value)
            else:
                instance.tags.update(set(value))
            logger.debug(f"Applied tags (merged): {instance.tags}")

        elif key == "dependencies":
            # Merge dependency lists
            if not hasattr(instance, "dependencies") or not instance.dependencies:
                instance.dependencies = value
            else:
                # Add new dependencies (avoiding duplicates)
                current_deps = instance.dependencies
                new_deps = [d for d in value if d not in current_deps]
                if new_deps:
                    instance.dependencies = current_deps + new_deps
            logger.debug(f"Applied dependencies (merged): {instance.dependencies}")

        elif key in SETTINGS_PARAMS:
            # Parameters to be applied to settings object
            try:
                instance.settings.__setattr__(key, value)
                logger.debug(f"Applied setting parameter: {key}={value}")
            except AttributeError:
                logger.warning(f"Failed to set {key} on settings object")

        elif key not in CONSTRUCTION_PARAMS:
            # Other runtime parameters are saved to runtime kwargs
            runtime_kwargs[key] = value
            logger.debug(f"Saved runtime parameter: {key}={value}")
