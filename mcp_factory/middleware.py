"""
MCP Factory Middleware Utilities

Provides reusable middleware loading functions for both factory and project levels.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def load_middleware_from_config(config: dict[str, Any]) -> list[Any] | None:
    """Load middleware instances from configuration

    This function can be used by both factory and project levels.

    Args:
        config: Configuration dictionary containing middleware section

    Returns:
        List of middleware instances or None
    """
    middleware_config = config.get("middleware", [])
    if not middleware_config:
        return None

    middleware_instances = []

    for middleware_def in middleware_config:
        if not middleware_def.get("enabled", True):
            continue

        middleware_type = middleware_def.get("type")
        middleware_config_params = middleware_def.get("config", {})

        try:
            if middleware_type == "custom":
                # Handle custom middleware
                middleware_class = middleware_def.get("class")
                if not middleware_class:
                    logger.error("Custom middleware missing 'class' field: %s", middleware_def)
                    continue

                # Import and instantiate custom middleware
                middleware_instance = _load_custom_middleware(
                    middleware_class,
                    middleware_def.get("args", []),
                    middleware_def.get("kwargs", {}),
                    middleware_config_params,
                )

            elif middleware_type in ["timing", "logging", "rate_limiting", "error_handling"]:
                # Handle built-in middleware types
                middleware_instance = _create_builtin_middleware(middleware_type, middleware_config_params)

            else:
                logger.error("Unknown middleware type: %s", middleware_type)
                continue

            if middleware_instance:
                middleware_instances.append(middleware_instance)
                logger.info("Loaded middleware: %s", middleware_type)

        except Exception as e:
            logger.error("Failed to load middleware %s: %s", middleware_type, e)
            continue

    return middleware_instances if middleware_instances else None


def _load_custom_middleware(class_path: str, args: list[Any], kwargs: dict[str, Any], config: dict[str, Any]) -> Any:
    """Load custom middleware class

    Args:
        class_path: Full path to middleware class (e.g., "my_project.middleware.CustomMiddleware")
        args: Constructor positional arguments
        kwargs: Constructor keyword arguments
        config: Middleware configuration

    Returns:
        Middleware instance
    """
    try:
        # Split module and class name
        module_path, class_name = class_path.rsplit(".", 1)

        # Import module
        import importlib

        module = importlib.import_module(module_path)

        # Get class
        middleware_class = getattr(module, class_name)

        # Merge config into kwargs
        final_kwargs = {**kwargs, **config}

        # Create instance
        return middleware_class(*args, **final_kwargs)

    except Exception as e:
        logger.error("Failed to load custom middleware %s: %s", class_path, e)
        raise


def _create_builtin_middleware(middleware_type: str, config: dict[str, Any]) -> Any:
    """Create built-in middleware instance using FastMCP official implementations

    Args:
        middleware_type: Type of built-in middleware
        config: Middleware configuration

    Returns:
        Middleware instance or None
    """
    try:
        # Import FastMCP official middleware implementations
        if middleware_type == "timing":
            from fastmcp.server.middleware.timing import TimingMiddleware

            return TimingMiddleware(logger=config.get("logger"), log_level=config.get("log_level", 20))

        if middleware_type == "logging":
            from fastmcp.server.middleware.logging import LoggingMiddleware

            return LoggingMiddleware(
                logger=config.get("logger"),
                log_level=config.get("log_level", 20),
                include_payloads=config.get("include_payloads", False),
                max_payload_length=config.get("max_payload_length", 1000),
            )

        if middleware_type == "rate_limiting":
            from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware

            return RateLimitingMiddleware(
                max_requests_per_second=config.get("max_requests_per_second", 10.0),
                burst_capacity=config.get("burst_capacity"),
                get_client_id=config.get("get_client_id"),
                global_limit=config.get("global_limit", False),
            )

        if middleware_type == "error_handling":
            from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware

            return ErrorHandlingMiddleware(
                logger=config.get("logger"),
                include_traceback=config.get("include_traceback", False),
                error_callback=config.get("error_callback"),
                transform_errors=config.get("transform_errors", True),
            )

        logger.error("Unknown builtin middleware type: %s", middleware_type)
        return None

    except ImportError as e:
        logger.error("Failed to import FastMCP middleware '%s': %s", middleware_type, e)
        return None
    except Exception as e:
        logger.error("Failed to create FastMCP middleware '%s': %s", middleware_type, e)
        return None
