"""ManagedServer - Extended FastMCP class with self-management capabilities.

Registers FastMCP's own public methods as server management tools, supporting JWT scope-based permission control.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import textwrap
import time
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP
from fastmcp.tools.tool import Tool, ToolAnnotations

# Update import path
from .auth import check_annotation_type, format_permission_error
from .exceptions import ServerError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

# Set up logging
logger = logging.getLogger(__name__)


class ManagedServer(FastMCP):
    """Extended FastMCP class that registers its own management methods as MCP tools."""

    # =============================================================================
    # Class Constants Definition
    # =============================================================================

    # Define annotation templates to avoid repetition
    _ANNOTATION_TEMPLATES = {
        "readonly": {  # Read-only query type
            "readOnlyHint": True,
            "destructiveHint": False,
            "openWorldHint": False,
        },
        "modify": {  # Modify but non-destructive
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": False,
        },
        "destructive": {  # Destructive operations
            "readOnlyHint": False,
            "destructiveHint": True,
            "openWorldHint": False,
        },
        "external": {  # Involving external systems
            "readOnlyHint": False,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    }

    # Meta management tools (tools that should not be cleared)
    _META_MANAGEMENT_TOOLS = {
        "manage_get_management_tools_info",
        "manage_clear_management_tools",
        "manage_recreate_management_tools",
        "manage_reset_management_tools",
    }

    # =============================================================================
    # Initialization Methods
    # =============================================================================

    def __init__(
        self,
        *,
        expose_management_tools: bool = True,
        enable_permission_check: bool | None = None,
        management_tool_tags: set[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ManagedServer.

        Args:
            expose_management_tools: Whether to expose FastMCP methods as management tools (default: True)
            enable_permission_check: Whether to enable JWT permission check
            management_tool_tags: Management tool tag set (fastmcp 2.8.0+)
            **kwargs: All parameters for FastMCP
        """
        # 💾 Save configuration parameters
        self.expose_management_tools = expose_management_tools
        self.management_tool_tags = management_tool_tags or {"management", "admin"}

        # 🔒 Security default: enable permission check by default when exposing management tools
        if enable_permission_check is None:
            self.enable_permission_check = expose_management_tools
        else:
            self.enable_permission_check = enable_permission_check

        # 🏷️ Dynamic attribute declaration (set by Factory)
        self._config: dict[str, Any] = {}
        self._server_id: str = ""
        self._created_at: str = ""
        self._project_path: str = ""

        # ⚠️ Security warning: warn when dangerous configuration
        self._validate_security_config()

        # Log initialization information
        server_name = kwargs.get("name", "ManagedServer")
        logger.info(f"Initializing ManagedServer: {server_name}")
        logger.info(
            f"Expose management tools: {expose_management_tools}, Permission check: {self.enable_permission_check}"
        )

        if expose_management_tools:
            # Create management tool object list
            management_tools = self._create_management_tools()
            logger.info(f"Created {len(management_tools)} management tools")

            # Merge business tools and management tools
            business_tools = kwargs.get("tools", [])
            kwargs["tools"] = business_tools + management_tools

        # Fix fastmcp 2.8.0 compatibility: change description to instructions
        if "description" in kwargs:
            kwargs["instructions"] = kwargs.pop("description")

        super().__init__(**kwargs)
        logger.info(f"ManagedServer {server_name} initialization completed")

    def _validate_security_config(self) -> None:
        """Validate security configuration."""
        if self.expose_management_tools and not self.enable_permission_check:
            import os
            import warnings

            # Detect if in production environment
            is_production = any(
                [
                    os.getenv("ENV") == "production",
                    os.getenv("ENVIRONMENT") == "production",
                    os.getenv("NODE_ENV") == "production",
                    os.getenv("FASTMCP_ENV") == "production",
                ]
            )

            if is_production:
                msg = (
                    "🚨 Production security error: Exposing management tools "
                    "with disabled permission check not allowed. "
                    "Set enable_permission_check=True or expose_management_tools=False"
                )
                raise ServerError(msg)
            warnings.warn(
                "⚠️ Security warning: Management tools are exposed but permission check is not enabled. "
                "This is dangerous in production! Recommend setting enable_permission_check=True or configuring auth",
                UserWarning,
                stacklevel=3,
            )

    # =============================================================================
    # Core Configuration - Management Method Definition
    # =============================================================================

    def _get_management_methods(self) -> dict[str, dict[str, Any]]:
        """Get management method configuration dictionary."""

        # Custom management methods (defined in ManagedServer class, guaranteed to exist)
        self_implemented_methods = {
            # Meta management tools - Manage management tools themselves
            "get_management_tools_info": {
                "description": "Get information and status of currently registered management tools",
                "async": False,
                "title": "View management tool information",
                "annotation_type": "readonly",
                "no_params": True,
                "tags": {"readonly", "safe", "meta", "introspection"},
                "enabled": True,
            },
            "clear_management_tools": {
                "description": "Clear all registered management tools (excluding meta management tools)",
                "async": False,
                "title": "Clear management tools",
                "annotation_type": "destructive",
                "no_params": True,
                "tags": {"admin", "destructive", "dangerous", "meta"},
                "enabled": True,
            },
            "recreate_management_tools": {
                "description": "Recreate all management tools (smart deduplication, won't affect meta tools)",
                "async": False,
                "title": "Recreate management tools",
                "annotation_type": "modify",
                "no_params": True,
                "tags": {"admin", "modify", "meta", "recovery"},
                "enabled": True,
            },
            "reset_management_tools": {
                "description": "Completely reset management tool system (clear then rebuild, dangerous operation)",
                "async": False,
                "title": "Reset management tool system",
                "annotation_type": "destructive",
                "no_params": True,
                "tags": {"admin", "destructive", "dangerous", "meta", "emergency"},
                "enabled": True,
            },
            "toggle_management_tool": {
                "description": "Dynamically enable/disable specified management tool",
                "async": False,
                "title": "Toggle tool status",
                "annotation_type": "modify",
                "tags": {"admin", "modify", "meta", "dynamic"},
                "enabled": True,
            },
            "get_tools_by_tags": {
                "description": "Filter and display management tools by tags",
                "async": False,
                "title": "Query tools by tags",
                "annotation_type": "readonly",
                "tags": {"readonly", "safe", "meta", "query"},
                "enabled": True,
            },
        }

        # FastMCP native methods (inherited from FastMCP, need existence check)
        fastmcp_native_methods = {
            # Query methods - Safe, read-only operations
            "get_tools": {
                "description": "Get all registered tools on the server",
                "async": True,
                "title": "View tool list",
                "annotation_type": "readonly",
                "no_params": True,
                "tags": {"readonly", "safe", "query"},
                "enabled": True,
            },
            "get_resources": {
                "description": "Get all registered resources on the server",
                "async": True,
                "title": "View resource list",
                "annotation_type": "readonly",
                "no_params": True,
                "tags": {"readonly", "safe", "query"},
                "enabled": True,
            },
            "get_resource_templates": {
                "description": "Get all registered resource templates on the server",
                "async": True,
                "title": "View resource templates",
                "annotation_type": "readonly",
                "no_params": True,
                "tags": {"readonly", "safe", "query"},
                "enabled": True,
            },
            "get_prompts": {
                "description": "Get all registered prompts on the server",
                "async": True,
                "title": "View prompt templates",
                "annotation_type": "readonly",
                "no_params": True,
                "tags": {"readonly", "safe", "query"},
                "enabled": True,
            },
            # Server composition management - High-risk operations
            "mount": {
                "description": "Mount another FastMCP server to the current server",
                "async": False,
                "title": "Mount server",
                "annotation_type": "external",
                "tags": {"admin", "external", "dangerous", "composition"},
                "enabled": True,
            },
            "import_server": {
                "description": "Import all tools and resources from another FastMCP server",
                "async": True,
                "title": "Import server",
                "annotation_type": "external",
                "tags": {"admin", "external", "dangerous", "composition"},
                "enabled": True,
            },
            # Dynamic management - Medium risk operations
            "add_tool": {
                "description": "Dynamically add tool to server",
                "async": False,
                "title": "Add tool",
                "annotation_type": "modify",
                "tags": {"admin", "modify", "dynamic"},
                "enabled": True,
            },
            "remove_tool": {
                "description": "Remove specified tool from server",
                "async": False,
                "title": "Remove tool",
                "annotation_type": "destructive",
                "tags": {"admin", "destructive", "dangerous", "dynamic"},
                "enabled": True,
            },
            "add_resource": {
                "description": "Dynamically add resource to server",
                "async": False,
                "title": "Add resource",
                "annotation_type": "modify",
                "tags": {"admin", "modify", "dynamic"},
                "enabled": True,
            },
            "add_prompt": {
                "description": "Dynamically add prompt to server",
                "async": False,
                "title": "Add prompt template",
                "annotation_type": "modify",
                "tags": {"admin", "modify", "dynamic"},
                "enabled": True,
            },
            "add_template": {
                "description": "Add a resource template to the server",
                "async": False,
                "title": "Add resource template",
                "annotation_type": "modify",
                "tags": {"admin", "modify", "dynamic"},
                "enabled": True,
            },
            "add_resource_fn": {
                "description": "Add a resource or template to the server from a function",
                "async": False,
                "title": "Add resource from function",
                "annotation_type": "modify",
                "tags": {"admin", "modify", "dynamic", "advanced"},
                "enabled": True,
            },
            "add_middleware": {
                "description": "Add middleware to the server",
                "async": False,
                "title": "Add middleware",
                "annotation_type": "modify",
                "tags": {"admin", "modify", "middleware", "advanced"},
                "enabled": True,
            },
            # Tool Transformation - FastMCP 2.8.0+ feature
            "transform_tool": {
                "description": "Transform existing tools using Tool Transformation API. Use manage_get_tools.",
                "async": False,
                "title": "Transform tool",
                "annotation_type": "modify",
                "tags": {"admin", "modify", "transform", "advanced"},
                "enabled": True,
            },
        }

        # Merge methods: custom management methods + existing FastMCP native methods
        result = self_implemented_methods.copy()

        for method_name, config in fastmcp_native_methods.items():
            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                result[method_name] = config
            else:
                logger.debug(f"FastMCP method '{method_name}' not available in current version, skipping")

        return result

    # =============================================================================
    # Tool Creation Main Logic
    # =============================================================================

    def _create_management_tools(self) -> list[Tool]:
        """Create management tool object list."""
        management_methods = self._get_management_methods()
        all_tool_names = {f"manage_{method_name}" for method_name in management_methods}

        logger.debug(f"Defined {len(management_methods)} management methods")

        result = self._create_tools_from_names(all_tool_names, management_methods, use_tool_objects=True)
        # Since use_tool_objects=True, result should be list[Tool]
        assert isinstance(result, list), "Expected list of tools when use_tool_objects=True"
        return result

    def _create_tools_from_names(
        self,
        tool_names: set[str],
        management_methods: dict[str, dict[str, Any]],
        use_tool_objects: bool = False,
    ) -> list[Tool] | int:
        """Unified tool creation logic."""
        created_tools: list[Tool] = []
        created_count = 0

        for tool_name in tool_names:
            method_name = tool_name[7:]  # Remove "manage_" prefix

            if method_name not in management_methods:
                logger.warning(f"Configuration for method {method_name} not found, skipping creation of {tool_name}")
                continue

            config = management_methods[method_name]

            if not config.get("enabled", True):
                logger.debug(f"Skipping disabled management tool: {tool_name}")
                continue

            try:
                # Dynamically generate wrapper and parameter definitions
                wrapper, parameters = self._create_method_wrapper_with_params(
                    method_name, config, config["annotation_type"]
                )

                # Build annotations and tags
                annotation_dict = self._ANNOTATION_TEMPLATES[config["annotation_type"]].copy()
                annotation_dict["title"] = config["title"]
                annotations = ToolAnnotations(
                    title=str(config["title"]),  # Ensure title is string type
                    readOnlyHint=annotation_dict.get("readOnlyHint"),
                    destructiveHint=annotation_dict.get("destructiveHint"),
                    openWorldHint=annotation_dict.get("openWorldHint"),
                )
                tool_tags: set[str] = set(config.get("tags", set())) | self.management_tool_tags

                if use_tool_objects:
                    tool = Tool(
                        name=tool_name,
                        description=config["description"],
                        parameters=parameters,
                        annotations=annotations,
                        tags=tool_tags,
                        enabled=config.get("enabled", True),
                    )
                    created_tools.append(tool)
                else:
                    self.tool(
                        name=tool_name,
                        description=config["description"],
                        annotations=annotation_dict,
                        tags=tool_tags,
                        enabled=config.get("enabled", True),
                    )(wrapper)

                created_count += 1
                logger.debug(f"Successfully created management tool: {tool_name}")

            except Exception as e:
                logger.error(f"Error occurred while creating management tool {tool_name}: {e}")
                continue

        result_msg = (
            f"Successfully created {len(created_tools)} management tool objects"
            if use_tool_objects
            else f"Successfully registered {created_count} management tools"
        )
        logger.info(result_msg)

        # Return different types based on use_tool_objects parameter
        return created_tools if use_tool_objects else created_count

    # =============================================================================
    # Wrapper Creation and Permission Control
    # =============================================================================

    def _create_method_wrapper_with_params(
        self, method_name: str, config: dict[str, Any], annotation_type: str
    ) -> tuple[Callable[..., str | Awaitable[str]], dict[str, Any]]:
        """Create method wrapper and generate parameter definitions."""
        # Check if it's a no-parameter method
        if config.get("no_params", False):
            wrapper = self._create_wrapper(
                method_name, config["description"], annotation_type, config["async"], has_params=False
            )
            logger.debug(f"Created no-parameter wrapper for method {method_name}")
            return wrapper, {}

        # Parameterized method: dynamically detect parameters
        try:
            original_method = getattr(self, method_name)
            sig = inspect.signature(original_method)
            parameters = self._generate_parameters_from_signature(sig, method_name)
            logger.debug(f"Detected {len(parameters)} parameters for method {method_name}")

            wrapper = self._create_wrapper(
                method_name, config["description"], annotation_type, config["async"], has_params=True
            )
            return wrapper, parameters

        except (AttributeError, TypeError) as e:
            logger.warning(
                f"Parameter detection failed for method {method_name}: {e}, fallback to no-parameter handling"
            )
            wrapper = self._create_wrapper(
                method_name, config["description"], annotation_type, config["async"], has_params=False
            )
            return wrapper, {}

    def _create_wrapper(
        self, name: str, desc: str, perm_type: str, is_async: bool, has_params: bool
    ) -> Callable[..., str | Awaitable[str]]:
        """Unified wrapper creation function."""

        def permission_check() -> str | None:
            """Unified permission check logic."""
            if self.enable_permission_check:
                permission_result = check_annotation_type(perm_type)
                if not permission_result.allowed:
                    logger.warning(f"Permission check failed: method {name}, permission type {perm_type}")
                    return format_permission_error(permission_result)
            return None

        def log_execution(action: str, execution_time: float | None = None) -> None:
            """Unified execution logging."""
            async_prefix = "Async" if is_async else "Sync"
            if execution_time is not None:
                logger.info(f"{async_prefix} management tool {name} {action}, took {execution_time:.3f} seconds")
            else:
                logger.info(f"Executing {async_prefix} management tool: {name}")

        def execute_method(original_method: Any, *args: Any, **kwargs: Any) -> Any:
            """Unified method execution logic."""
            if asyncio.iscoroutinefunction(original_method) and not is_async:
                logger.error(f"Error: execute_method used for async method {name}")
                return "❌ Internal error: async method should use async wrapper"

            if has_params:
                logger.debug(f"Executing {name} with parameters: args={args}, kwargs={kwargs}")
                if kwargs:
                    return original_method(**kwargs)
                if args:
                    return original_method(*args)
                return original_method()
            logger.debug(f"Executing {name} without parameters")
            return original_method()

        # Create wrapper
        if is_async:

            async def async_wrapper() -> str:
                perm_error = permission_check()
                if perm_error:
                    return perm_error

                try:
                    log_execution("started")
                    start_time = time.time()
                    original_method = getattr(self, name)

                    if has_params:
                        logger.warning(
                            f"Async method {name} requires parameters, but FastMCP doesn't support complex parameters"
                        )

                    result = await original_method()
                    execution_time = time.time() - start_time
                    log_execution("executed successfully", execution_time)
                    return self._format_tool_result(result)
                except (AttributeError, TypeError, ValueError) as e:
                    logger.error(f"Async management tool {name} execution failed: {e}", exc_info=True)
                    return f"❌ Execution error: {e!s}"

            wrapper = async_wrapper
        else:

            def sync_wrapper() -> str:
                perm_error = permission_check()
                if perm_error:
                    return perm_error

                try:
                    log_execution("started")
                    start_time = time.time()
                    original_method = getattr(self, name)

                    if has_params:
                        logger.warning(
                            f"Sync method {name} requires parameters, but FastMCP doesn't support complex parameters"
                        )

                    result = execute_method(original_method)
                    execution_time = time.time() - start_time
                    log_execution("executed successfully", execution_time)
                    return self._format_tool_result(result)
                except (AttributeError, TypeError, ValueError) as e:
                    logger.error(f"Sync management tool {name} execution failed: {e}", exc_info=True)
                    return f"❌ Execution error: {e!s}"

            wrapper = sync_wrapper  # type: ignore

        wrapper.__name__ = f"manage_{name}"
        wrapper.__doc__ = desc
        return wrapper

    # =============================================================================
    # Public Management Interface
    # =============================================================================

    def get_management_tools_info(self) -> str:
        """Get information about currently registered management tools."""
        return self._safe_execute("get management tools info", self._get_management_tools_info_impl)

    def clear_management_tools(self) -> str:
        """Clear all registered management tools."""
        return self._safe_execute("clear management tools", self._clear_management_tools_impl)

    def recreate_management_tools(self) -> str:
        """Recreate all management tools."""
        return self._safe_execute("recreate management tools", self._recreate_management_tools_impl)

    def reset_management_tools(self) -> str:
        """Completely reset the management tools system."""
        return self._safe_execute("reset management tools system", self._reset_management_tools_impl)

    def toggle_management_tool(self, tool_name: str, enabled: bool | None = None) -> str:
        """Dynamically enable/disable management tools."""
        return self._safe_execute("toggle tool status", lambda: self._toggle_management_tool_impl(tool_name, enabled))

    def get_tools_by_tags(self, include_tags: set[str] | None = None, exclude_tags: set[str] | None = None) -> str:
        """Query management tools by tags."""
        return self._safe_execute(
            "query tools by tags", lambda: self._get_tools_by_tags_impl(include_tags, exclude_tags)
        )

    def transform_tool(self, source_tool_name: str, new_tool_name: str, transform_config: str = "{}") -> str:
        """Transform existing tools using the official Tool Transformation API."""
        return self._safe_execute(
            "tool transformation", lambda: self._transform_tool_impl(source_tool_name, new_tool_name, transform_config)
        )

    # =============================================================================
    # Management Interface Implementation
    # =============================================================================

    def _safe_execute(self, operation: str, func: Callable[[], str]) -> str:
        """Unified wrapper for safe operation execution."""
        try:
            logger.info(f"Starting {operation}")
            result = func()
            logger.info(f"{operation} successful")
            return result
        except Exception as e:
            error_msg = f"❌ Error occurred during {operation}: {e}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def _get_management_tools_info_impl(self) -> str:
        """Implementation for getting management tools information."""
        if not hasattr(self, "_tool_manager") or not hasattr(self._tool_manager, "_tools"):
            return "📋 Tool manager or tool list not found"

        tools = self._tool_manager._tools
        management_tools = {
            name: tool for name, tool in tools.items() if isinstance(name, str) and name.startswith("manage_")
        }

        if not management_tools:
            return "📋 No management tools currently registered"

        info_lines = [f"📋 Management Tools Information (Total: {len(management_tools)}):"]

        for tool_name, tool in management_tools.items():
            description = getattr(tool, "description", "No description")
            annotations = getattr(tool, "annotations", {})

            # Extract key information
            if hasattr(annotations, "destructiveHint"):
                is_destructive = getattr(annotations, "destructiveHint", False)
                is_readonly = getattr(annotations, "readOnlyHint", False)
                title = getattr(annotations, "title", tool_name)
            elif isinstance(annotations, dict):
                is_destructive = annotations.get("destructiveHint", False)
                is_readonly = annotations.get("readOnlyHint", False)
                title = annotations.get("title", tool_name)
            else:
                is_destructive = False
                is_readonly = False
                title = tool_name

            # Add security indicators
            safety_icon = "🔒" if is_destructive else ("👁️" if is_readonly else "⚙️")
            info_lines.append(f"  {safety_icon} {tool_name}: {title}")
            if description != tool_name:
                info_lines.append(f"    Description: {description}")

        return "\n".join(info_lines)

    def _clear_management_tools_impl(self) -> str:
        """Implementation for clearing management tools."""
        removed_count = self._clear_management_tools()
        return f"✅ Successfully cleared {removed_count} management tools"

    def _recreate_management_tools_impl(self) -> str:
        """Implementation for recreating management tools."""
        existing_tools = self._get_management_tool_names()
        management_methods = self._get_management_methods()
        expected_tools = {f"manage_{method_name}" for method_name in management_methods}
        missing_tools = expected_tools - existing_tools

        logger.debug(f"Currently {len(existing_tools)} exist, found {len(missing_tools)} missing management tools")

        if not missing_tools:
            return "✅ All management tools already exist, no need to recreate"

        created_count = self._create_tools_from_names(missing_tools, management_methods, use_tool_objects=False)
        return f"✅ Successfully recreated {created_count} management tools"

    def _reset_management_tools_impl(self) -> str:
        """Implementation for resetting management tools."""
        cleared_count = self._clear_management_tools()
        logger.info(f"Cleared {cleared_count} management tools")

        management_methods = self._get_management_methods()
        all_tool_names = {f"manage_{method_name}" for method_name in management_methods}
        recreated_count = self._create_tools_from_names(all_tool_names, management_methods, use_tool_objects=False)

        return f"🔄 Management tools system reset complete: cleared {cleared_count}, rebuilt {recreated_count}"

    def _toggle_management_tool_impl(self, tool_name: str, enabled: bool | None) -> str:
        """Implementation for toggling management tool status."""
        # Normalize tool name
        if not tool_name.startswith("manage_"):
            tool_name = f"manage_{tool_name}"

        # Check if tool exists
        if not hasattr(self, "_tool_manager") or not hasattr(self._tool_manager, "_tools"):
            return "❌ Tool manager not found"

        if tool_name not in self._tool_manager._tools:
            available_tools = [
                name for name in self._tool_manager._tools if isinstance(name, str) and name.startswith("manage_")
            ]
            return f"❌ Management tool {tool_name} does not exist\nAvailable tools: {', '.join(available_tools)}"

        # Get current tool object
        tool = self._tool_manager._tools[tool_name]
        current_enabled = getattr(tool, "enabled", True)

        # Determine new status
        new_enabled = not current_enabled if enabled is None else enabled

        # Update tool status
        if hasattr(tool, "enabled"):
            tool.enabled = new_enabled
            action = "enabled" if new_enabled else "disabled"
            return f"✅ {action.capitalize()} management tool: {tool_name}"
        return f"⚠️ Tool {tool_name} does not support dynamic enable/disable functionality"

    def _get_tools_by_tags_impl(self, include_tags: set[str] | None, exclude_tags: set[str] | None) -> str:
        """Implementation for querying tools by tags."""
        logger.debug(f"Querying tools by tags: include={include_tags}, exclude={exclude_tags}")

        if not hasattr(self, "_tool_manager") or not hasattr(self._tool_manager, "_tools"):
            return "📋 Tool manager not found"

        tools = self._tool_manager._tools
        management_tools = {
            name: tool for name, tool in tools.items() if isinstance(name, str) and name.startswith("manage_")
        }

        if not management_tools:
            return "📋 No management tools currently available"

        # Filter by tags
        filtered_tools = {}
        for tool_name, tool in management_tools.items():
            tool_tags: set[str] = getattr(tool, "tags", set())

            # Check include tags
            if include_tags and not (tool_tags & include_tags):
                continue

            # Check exclude tags
            if exclude_tags and (tool_tags & exclude_tags):
                continue

            filtered_tools[tool_name] = tool

        if not filtered_tools:
            return f"📋 No tools match the criteria\nFilter conditions: include {include_tags}, exclude {exclude_tags}"

        # Format results
        info_lines = [f"📋 Query Results (Total: {len(filtered_tools)}):"]
        for tool_name, tool in filtered_tools.items():
            description = getattr(tool, "description", "No description")
            tags: set[str] = getattr(tool, "tags", set())
            enabled = getattr(tool, "enabled", True)
            status_icon = "✅" if enabled else "❌"

            info_lines.append(f"  {status_icon} {tool_name}")
            info_lines.append(f"    Description: {description}")
            info_lines.append(f"    Tags: {', '.join(sorted(tags))}")

        return "\n".join(info_lines)

    def _transform_tool_impl(self, source_tool_name: str, new_tool_name: str, transform_config: str) -> str:
        """Implementation for tool transformation."""
        import json

        try:
            from fastmcp.tools import Tool
            from fastmcp.tools.tool_transform import ArgTransform
        except ImportError as e:
            return f"❌ Tool Transformation functionality not available: {e}"

        # Parse transformation configuration
        try:
            config = json.loads(transform_config) if transform_config.strip() else {}
        except json.JSONDecodeError as e:
            return f"❌ Transformation configuration JSON format error: {e}"

        # Get source tool
        if not hasattr(self, "_tool_manager") or not hasattr(self._tool_manager, "_tools"):
            return "❌ Tool manager not available"

        source_tool = self._tool_manager._tools.get(source_tool_name)
        if not source_tool:
            return f"❌ Source tool '{source_tool_name}' does not exist"

        # Check if new tool name already exists
        if new_tool_name in self._tool_manager._tools:
            return f"❌ Tool name '{new_tool_name}' already exists"

        # Build transformation arguments
        transform_args = {}
        for param_name, param_config in config.get("transform_args", {}).items():
            transform_args[param_name] = ArgTransform(
                name=param_config.get("name", param_name),
                description=param_config.get("description", f"Transform parameter {param_name}"),
                default=param_config.get("default"),
            )

        # Perform tool transformation using official API
        transformed_tool = Tool.from_tool(
            source_tool,
            name=new_tool_name,
            description=config.get("description", f"Transformed from {source_tool_name}"),
            transform_args=transform_args,
        )

        # Add transformed tool to server
        self.add_tool(transformed_tool)

        result = textwrap.dedent(f"""
            ✅ Tool Transformation successful!

            🔧 Transformation Details:
            - Source tool: {source_tool_name}
            - New tool: {new_tool_name}
            - Transformation type: Official Tool.from_tool() API
            - Transform parameters: {len(transform_args)}

            📊 Transformation Configuration:
            {json.dumps(config, indent=2, ensure_ascii=False)}

            🎯 New tool has been added to the server and is ready to use!
        """).strip()

        logger.info(f"🎯 Successfully transformed tool: {source_tool_name} -> {new_tool_name}")
        return result

    # =============================================================================
    # Internal Helper Methods
    # =============================================================================

    def _get_management_tool_count(self) -> int:
        """Get the current number of management tools."""
        if hasattr(self, "_tool_manager") and hasattr(self._tool_manager, "_tools"):
            return len(
                [name for name in self._tool_manager._tools if isinstance(name, str) and name.startswith("manage_")]
            )
        return 0

    def _get_management_tool_names(self) -> set[str]:
        """Get the set of current management tool names."""
        if hasattr(self, "_tool_manager") and hasattr(self._tool_manager, "_tools"):
            return {name for name in self._tool_manager._tools if isinstance(name, str) and name.startswith("manage_")}
        return set()

    def _clear_management_tools(self) -> int:
        """Internal method: Clear all registered management tools."""
        removed_count = 0

        try:
            if hasattr(self, "_tool_manager") and hasattr(self._tool_manager, "_tools"):
                tool_names = list(self._tool_manager._tools.keys())

                for tool_name in tool_names:
                    if (
                        isinstance(tool_name, str)
                        and tool_name.startswith("manage_")
                        and tool_name not in self._META_MANAGEMENT_TOOLS
                    ):
                        try:
                            self.remove_tool(tool_name)
                            removed_count += 1
                            logger.debug(f"Removed management tool: {tool_name}")
                        except Exception as e:
                            logger.warning(f"Error removing tool {tool_name}: {e}")

            logger.info(
                f"Successfully cleared {removed_count} management tools (preserved {len(self._META_MANAGEMENT_TOOLS)})"
            )
            return removed_count

        except Exception as e:
            logger.error(f"Error occurred while clearing management tools: {e}", exc_info=True)
            return removed_count

    def _generate_parameters_from_signature(self, sig: inspect.Signature, method_name: str) -> dict[str, Any]:
        """Generate parameter definitions from method signature."""
        parameters = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_info = {"description": f"Parameter {param_name} for {method_name}"}

            # Infer parameter type based on type annotation
            if param.annotation != inspect.Parameter.empty:
                param_type = self._map_python_type_to_json_schema(param.annotation)
                param_info["type"] = param_type
            else:
                param_info["type"] = "string"

            # Handle default values
            if param.default != inspect.Parameter.empty:
                if param.default is None:
                    param_info["default"] = "null"
                else:
                    param_info["default"] = str(param.default)
            else:
                param_info["required"] = "true"

            parameters[param_name] = param_info

        return parameters

    def _map_python_type_to_json_schema(self, python_type: Any) -> str:
        """Map Python types to JSON Schema types."""
        type_mapping = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}

        if python_type in type_mapping:
            return type_mapping[python_type]
        if hasattr(python_type, "__origin__"):
            origin = python_type.__origin__
            if origin is list:
                return "array"
            if origin is dict:
                return "object"
        return "string"

    def _format_tool_result(self, result: Any) -> str:
        """Format tool execution result as string."""
        try:
            if isinstance(result, dict):
                if not result:
                    return "📋 No data"

                formatted_lines = []
                for key, value in result.items():
                    if isinstance(value, dict) and hasattr(value, "name"):
                        name = getattr(value, "name", key)
                        desc = getattr(value, "description", "No description")
                        formatted_lines.append(f"• {name}: {desc}")
                    else:
                        formatted_lines.append(f"• {key}: {value}")

                return "\n".join(formatted_lines)

            if isinstance(result, list | tuple):
                if not result:
                    return "📋 Empty list"
                return f"📋 Total {len(result)} items:\n" + "\n".join(f"• {item}" for item in result)

            if result is None:
                return "✅ Operation completed"

            return str(result)

        except Exception as e:
            logger.error(f"Error occurred while formatting result: {e}", exc_info=True)
            return f"⚠️ Result formatting error: {e}"
