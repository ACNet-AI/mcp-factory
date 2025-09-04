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
from fastmcp.tools.tool import Tool
from mcp.types import ToolAnnotations

from ..authorization import get_current_user_info
from ..exceptions import ServerError
from .tool_configs import (
    get_fastmcp_native_methods,
    get_self_implemented_methods,
    get_user_permission_tools,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

# Set up logging
logger = logging.getLogger(__name__)


class ManagedServer(FastMCP[Any]):
    """Extended FastMCP class with self-management capabilities and authentication support.

    Extends FastMCP by adding:
    - Automatic registration of management tools
    - Scope-based permission control
    - Support for multiple authentication providers

    See __init__ method for authentication options and detailed examples.
    """

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

    # Management tool prefix constant
    _MANAGEMENT_TOOL_PREFIX = "manage_"

    # Meta management tools (tools that should not be cleared)
    _META_MANAGEMENT_TOOLS = {
        "manage_get_management_tools_info",
        "manage_clear_management_tools",
        "manage_recreate_management_tools",
        "manage_reset_management_tools",
    }

    @classmethod
    def _is_management_tool(cls, tool_name: str) -> bool:
        """Check if a tool name is a management tool."""
        return isinstance(tool_name, str) and tool_name.startswith(cls._MANAGEMENT_TOOL_PREFIX)

    # =============================================================================
    # Initialization Methods
    # =============================================================================

    def __init__(
        self,
        *,
        expose_management_tools: bool = True,
        authorization: bool | None = None,
        management_tool_tags: set[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ManagedServer.

        Args:
            expose_management_tools: Whether to expose FastMCP methods as management tools (default: True)

            authorization: Authorization configuration (bool | None)
                * None (default): Infer from auth parameter - no auth means no authorization, with auth means enable authorization
                * True: Force enable authorization (uses Casbin RBAC system)
                * False: Force disable authorization (all permissions allowed)
            management_tool_tags: Management tool tag set (fastmcp 2.8.0+)
            **kwargs: All parameters for FastMCP, including:
                - auth: Authentication provider (AuthProvider | None | NotSetT)
                    * NotSet (default): Use FastMCP default behavior (checks environment variables)
                    * None: No authentication required
                    * JWTVerifier: JWT token authentication with key verification
                    * TokenVerifier: Simple bearer token verification
                    * InMemoryOAuthProvider: Built-in OAuth server (testing/development)
                    * OAuthProxy: External OAuth providers (GitHub, Google, etc.)
                    * Custom implementations: Any class implementing AuthProvider interface
                - name: Server name (required)
                - instructions: Server description
                - tools: List of tools to register

        Examples:
            # Default behavior - infer authorization from auth parameter
            server = ManagedServer(name="my-server")  # Auto-infer based on auth

            # Explicit authorization control
            server = ManagedServer(name="secure-server", authorization=True)   # Force enable
            server = ManagedServer(name="open-server", authorization=False)    # Force disable

            # Combined with authentication
            from fastmcp.server.auth.providers.jwt import JWTVerifier, RSAKeyPair

            # JWT authentication with authorization
            key_pair = RSAKeyPair.generate()
            jwt_auth = JWTVerifier(public_key=key_pair.public_key)
            server = ManagedServer(
                name="jwt-server",
                auth=jwt_auth,
                authorization=True  # Explicit enable
            )

            # OAuth authentication with auto-inferred authorization
            from fastmcp.server.auth import OAuthProxy
            proxy_auth = OAuthProxy(providers=["github", "google"])
            server = ManagedServer(
                name="oauth-server",
                auth=proxy_auth  # authorization=None will auto-enable
            )

            # Public server with no auth or authorization
            server = ManagedServer(
                name="public-server",
                auth=None,
                authorization=False
            )
        """
        # 💾 Save configuration parameters
        self.expose_management_tools = expose_management_tools
        self.management_tool_tags = management_tool_tags or {"management", "admin"}

        # 🔒 Setup authorization system
        self.authorization = self._setup_authorization(authorization, kwargs.get("auth"), expose_management_tools)

        # Initialize authorization manager if needed
        self._authorization_manager = None
        if self.authorization:
            try:
                from ..authorization.manager import MCPAuthorizationManager

                self._authorization_manager = MCPAuthorizationManager()
                logger.info("Authorization manager initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize authorization manager: {e}")
                self._authorization_manager = None

        # 🏷️ Dynamic attribute declaration (set by Factory)
        self._config: dict[str, Any] = {}
        self._server_id: str = ""
        self._created_at: str = ""

        # ⚠️ Security warning: warn when dangerous configuration
        self._validate_security_config()

        # Log initialization information
        server_name = kwargs.get("name", "ManagedServer")
        logger.info("Initializing ManagedServer: %s", server_name)
        logger.info(f"Expose management tools: {expose_management_tools}, Permission check: {self.authorization}")

        if expose_management_tools:
            # Create management tool object list
            management_tools = self._create_management_tools()
            logger.info("Created %s management tools", len(management_tools))

            # Merge business tools and management tools
            business_tools = kwargs.get("tools", [])
            kwargs["tools"] = business_tools + management_tools

        # Fix fastmcp 2.8.0 compatibility: change description to instructions
        if "description" in kwargs:
            kwargs["instructions"] = kwargs.pop("description")

        super().__init__(**kwargs)

        # Register user permission tools (separate from management tools)
        if self.authorization:
            self._register_user_permission_tools()

        logger.info("ManagedServer %s initialization completed", server_name)

    def _setup_authorization(self, authorization: Any, auth_provider: Any, expose_management_tools: bool) -> bool:
        """Setup authorization system based on parameters"""

        # Handle explicit authorization parameter
        if authorization is not None:
            if authorization is True:
                logger.info("Authorization explicitly enabled")
                return True
            elif authorization is False:
                logger.info("Authorization explicitly disabled")
                return False
            else:
                logger.warning(f"Invalid authorization value: {authorization}, using False")
                return False

        # Default behavior: infer from auth parameter
        if auth_provider is None:
            # No auth -> no authorization by default
            inferred = False
            logger.info("No auth provider -> authorization disabled")
        else:
            # Has auth -> enable authorization if exposing management tools
            inferred = expose_management_tools
            logger.info(f"Auth provider detected -> authorization {'enabled' if inferred else 'disabled'}")

        return inferred

    def _validate_security_config(self) -> None:
        """Validate security configuration."""
        if self.expose_management_tools and not self.authorization:
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
                    "Set authorization=True or expose_management_tools=False"
                )
                raise ServerError(msg)
            warnings.warn(
                "⚠️ Security warning: Management tools are exposed but permission check is not enabled. "
                "This is dangerous in production! Recommend setting authorization=True or configuring auth",
                UserWarning,
                stacklevel=3,
            )

    # =============================================================================
    # Core Configuration - Management Method Definition
    # =============================================================================

    def _get_management_methods(self) -> dict[str, dict[str, Any]]:
        """Get management method configuration dictionary."""
        # Load configurations from external config file
        self_implemented_methods = get_self_implemented_methods()
        fastmcp_native_methods = get_fastmcp_native_methods()

        # Merge methods: custom management methods + existing FastMCP native methods
        result = self_implemented_methods.copy()

        for method_name, config in fastmcp_native_methods.items():
            if hasattr(self, method_name) and callable(getattr(self, method_name)):
                result[method_name] = config
            else:
                logger.debug("FastMCP method '%s' not available in current version, skipping", method_name)

        return result

    # =============================================================================
    # Tool Creation Main Logic
    # =============================================================================

    def _create_management_tools(self) -> list[Tool]:
        """Create management tool object list."""
        management_methods = self._get_management_methods()
        all_tool_names = {f"{self._MANAGEMENT_TOOL_PREFIX}{method_name}" for method_name in management_methods}

        logger.debug("Defined %s management methods", len(management_methods))

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
            method_name = tool_name[len(self._MANAGEMENT_TOOL_PREFIX) :]  # Remove prefix

            if method_name not in management_methods:
                logger.warning("Configuration for method %s not found, skipping creation of %s", method_name, tool_name)
                continue

            config = management_methods[method_name]

            if not config.get("enabled", True):
                logger.debug("Skipping disabled management tool: %s", tool_name)
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
                logger.debug("Successfully created management tool: %s", tool_name)

            except Exception as e:
                logger.error("Error occurred while creating management tool %s: %s", tool_name, e)
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
            logger.debug("Created no-parameter wrapper for method %s", method_name)
            # Return proper JSON Schema for no-parameter methods
            return wrapper, {"type": "object", "properties": {}}

        # Parameterized method: dynamically detect parameters
        try:
            original_method = getattr(self, method_name)
            sig = inspect.signature(original_method)
            parameters = self._generate_parameters_from_signature(sig, method_name)
            logger.debug("Detected %s parameters for method %s", len(parameters), method_name)

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
            # Return proper JSON Schema for fallback case
            return wrapper, {"type": "object", "properties": {}}

    def _create_wrapper(
        self, name: str, desc: str, perm_type: str, is_async: bool, has_params: bool
    ) -> Callable[..., str | Awaitable[str]]:
        """Unified wrapper creation function."""

        def permission_check() -> str | None:
            """Unified permission check logic."""
            if self.authorization:
                # Use authorization system
                if hasattr(self, "_authorization_manager") and self._authorization_manager:
                    try:
                        user_id, _ = get_current_user_info()
                        if not user_id:
                            return "❌ Authentication required"

                        # Check permission using authorization manager
                        allowed = self._authorization_manager.check_annotation_permission(user_id, perm_type)
                        if not allowed:
                            logger.warning("Permission check failed: method %s, permission type %s", name, perm_type)
                            return f"❌ Insufficient permissions for {perm_type} operations"
                    except Exception as e:
                        logger.error("Authorization system error: %s", e)
                        return f"❌ Authorization system error: {e}"
                else:
                    # No authorization manager available
                    logger.warning("Authorization manager not available for permission check")
                    return "❌ Authorization system not available"
            return None

        def log_execution(action: str, execution_time: float | None = None) -> None:
            """Unified execution logging."""
            async_prefix = "Async" if is_async else "Sync"
            if execution_time is not None:
                logger.info("%s management tool %s %s, took %.3f seconds", async_prefix, name, action, execution_time)
            else:
                logger.info("Executing %s management tool: %s", async_prefix, name)

        def execute_method(original_method: Any, *args: Any, **kwargs: Any) -> Any:
            """Unified method execution logic."""
            if asyncio.iscoroutinefunction(original_method) and not is_async:
                logger.error("Error: execute_method used for async method %s", name)
                return "❌ Internal error: async method should use async wrapper"

            if has_params:
                logger.debug("Executing %s with parameters: args=%s, kwargs=%s", name, args, kwargs)
                if kwargs:
                    return original_method(**kwargs)
                if args:
                    return original_method(*args)
                return original_method()
            logger.debug("Executing %s without parameters", name)
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

    def get_management_tools_info(self) -> dict[str, Any]:
        """Get information about currently registered management tools."""
        try:
            return self._get_management_tools_info_impl()
        except Exception as e:
            logger.error("Error getting management tools info: %s", e, exc_info=True)
            return {
                "management_tools": [],
                "configuration": {
                    "expose_management_tools": self.expose_management_tools,
                    "authorization": self.authorization,
                    "management_tool_tags": list(self.management_tool_tags),
                },
                "statistics": {"total_management_tools": 0, "enabled_tools": 0, "permission_levels": {}},
                "error": str(e),
            }

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

    def debug_permission(self, user_id: str, resource: str, action: str, scope: str = "*") -> str:
        """Debug permission check process with detailed diagnostics."""
        return self._safe_execute(
            "permission debugging", lambda: self._debug_permission_impl(user_id, resource, action, scope)
        )

    def review_permission_requests(
        self, action: str = "list", request_id: str = "", review_action: str = "", comment: str = ""
    ) -> str:
        """Review and approve/reject permission requests."""
        return self._safe_execute(
            "permission request review",
            lambda: self._review_permission_requests_impl(action, request_id, review_action, comment),
        )

    # =============================================================================
    # Public Authorization API
    # =============================================================================

    @property
    def authz(self) -> Any:
        """Get the authorization manager instance.

        Returns:
            MCPAuthorizationManager: The authorization manager instance, or None if authorization is disabled.

        Example:
            ```python
            server = ManagedServer(name="my-server", authorization=True)
            if server.authz:
                server.authz.assign_role("alice", "premium_user", "admin", "User upgrade")
                can_access = server.authz.check_permission("alice", "tool", "execute", "premium")
            ```
        """
        return getattr(self, "_authorization_manager", None)

    def assign_role(self, user_id: str, role: str, assigned_by: str = "system", reason: str = "") -> bool:
        """Assign a role to a user.

        Args:
            user_id: The user ID to assign the role to
            role: The role to assign (e.g., 'premium_user', 'admin')
            assigned_by: Who is assigning the role (default: 'system')
            reason: Reason for the role assignment

        Returns:
            bool: True if successful, False otherwise

        Example:
            ```python
            success = server.assign_role("alice", "premium_user", "admin", "User purchased premium")
            ```
        """
        if not self.authz:
            logger.warning("Authorization not enabled, cannot assign role")
            return False

        try:
            result = self.authz.assign_role(user_id, role, assigned_by, reason)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to assign role {role} to user {user_id}: {e}")
            return False

    def revoke_role(self, user_id: str, role: str, revoked_by: str = "system", reason: str = "") -> bool:
        """Revoke a role from a user.

        Args:
            user_id: The user ID to revoke the role from
            role: The role to revoke
            revoked_by: Who is revoking the role (default: 'system')
            reason: Reason for the role revocation

        Returns:
            bool: True if successful, False otherwise

        Example:
            ```python
            success = server.revoke_role("alice", "premium_user", "admin", "Subscription expired")
            ```
        """
        if not self.authz:
            logger.warning("Authorization not enabled, cannot revoke role")
            return False

        try:
            result = self.authz.revoke_role(user_id, role, revoked_by, reason)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to revoke role {role} from user {user_id}: {e}")
            return False

    def check_permission(self, user_id: str, resource: str, action: str, scope: str = "*") -> bool:
        """Check if a user has a specific permission.

        Args:
            user_id: The user ID to check
            resource: The resource type (e.g., 'tool', 'mcp', 'resource')
            action: The action type (e.g., 'execute', 'read', 'write', 'admin')
            scope: The permission scope (e.g., '*', 'basic', 'premium', 'enterprise')

        Returns:
            bool: True if user has permission, False otherwise

        Example:
            ```python
            can_execute = server.check_permission("alice", "tool", "execute", "premium")
            ```
        """
        if not self.authz:
            logger.warning("Authorization not enabled, permission check returns True")
            return True

        try:
            result = self.authz.check_permission(user_id, resource, action, scope)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to check permission for user {user_id}: {e}")
            return False

    def get_user_roles(self, user_id: str) -> list[str]:
        """Get all roles assigned to a user.

        Args:
            user_id: The user ID to get roles for

        Returns:
            list[str]: List of role names assigned to the user

        Example:
            ```python
            roles = server.get_user_roles("alice")
            print(f"Alice has roles: {roles}")
            ```
        """
        if not self.authz:
            logger.warning("Authorization not enabled, returning empty roles list")
            return []

        try:
            result = self.authz.get_user_roles(user_id)
            return list(result) if result else []
        except Exception as e:
            logger.error(f"Failed to get roles for user {user_id}: {e}")
            return []

    def create_admin_user(self, user_id: str, reason: str = "Admin user creation") -> bool:
        """Create an admin user by assigning the admin role.

        Args:
            user_id: The user ID to make admin
            reason: Reason for creating admin user

        Returns:
            bool: True if successful, False otherwise

        Example:
            ```python
            success = server.create_admin_user("admin", "Initial setup")
            ```
        """
        return self.assign_role(user_id, "admin", "system", reason)

    # =============================================================================
    # Management Interface Implementation
    # =============================================================================

    def _safe_execute(self, operation: str, func: Callable[[], str]) -> str:
        """Unified wrapper for safe operation execution."""
        try:
            logger.info("Starting %s", operation)
            result = func()
            logger.info("%s successful", operation)
            return result
        except Exception as e:
            error_msg = f"❌ Error occurred during {operation}: {e}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def _get_management_tools_info_impl(self) -> dict[str, Any]:
        """Implementation for getting management tools information with structured output."""
        if not hasattr(self, "_tool_manager") or not hasattr(self._tool_manager, "_tools"):
            return self._get_empty_tools_info()

        management_tools = self._extract_management_tools()
        tool_info_list, statistics = self._build_tool_info_list(management_tools)

        return {
            "management_tools": tool_info_list,
            "configuration": self._get_configuration_info(),
            "statistics": statistics,
        }

    def _get_empty_tools_info(self) -> dict[str, Any]:
        """Return empty tools info structure."""
        return {
            "management_tools": [],
            "configuration": self._get_configuration_info(),
            "statistics": {"total_management_tools": 0, "enabled_tools": 0, "permission_levels": {}},
        }

    def _get_configuration_info(self) -> dict[str, Any]:
        """Get server configuration information."""
        return {
            "expose_management_tools": self.expose_management_tools,
            "authorization": self.authorization,
            "management_tool_tags": list(self.management_tool_tags),
        }

    def _extract_management_tools(self) -> dict[str, Any]:
        """Extract management tools from tool manager."""
        tools = self._tool_manager._tools
        return {name: tool for name, tool in tools.items() if self._is_management_tool(name)}

    def _build_tool_info_list(self, management_tools: dict[str, Any]) -> tuple[list[dict], dict[str, Any]]:
        """Build tool information list and statistics."""
        tool_info_list = []
        enabled_count = 0
        permission_levels: dict[str, int] = {}

        for tool_name, tool in management_tools.items():
            tool_info = self._create_tool_info(tool_name, tool)
            tool_info_list.append(tool_info)

            if tool_info["enabled"]:
                enabled_count += 1

            permission_level = tool_info["permission_level"]
            permission_levels[permission_level] = permission_levels.get(permission_level, 0) + 1

        statistics = {
            "total_management_tools": len(management_tools),
            "enabled_tools": enabled_count,
            "permission_levels": permission_levels,
        }

        return tool_info_list, statistics

    def _create_tool_info(self, tool_name: str, tool: Any) -> dict[str, Any]:
        """Create information dictionary for a single tool."""
        description = getattr(tool, "description", "No description")
        annotations = getattr(tool, "annotations", {})
        enabled = getattr(tool, "enabled", True)
        permission_level = self._determine_permission_level(annotations)

        return {
            "name": tool_name,
            "description": description,
            "permission_level": permission_level,
            "enabled": enabled,
            "annotations": dict(annotations) if isinstance(annotations, dict) else {},
        }

    def _determine_permission_level(self, annotations: Any) -> str:
        """Determine permission level from tool annotations."""
        # Extract permission hints
        if hasattr(annotations, "destructiveHint"):
            is_destructive = getattr(annotations, "destructiveHint", False)
            is_readonly = getattr(annotations, "readOnlyHint", False)
        elif isinstance(annotations, dict):
            is_destructive = annotations.get("destructiveHint", False)
            is_readonly = annotations.get("readOnlyHint", False)
        else:
            is_destructive = False
            is_readonly = False

        # Determine permission level
        if is_destructive:
            return "destructive"
        elif is_readonly:
            return "readonly"
        else:
            return "modify"

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

        logger.debug("Currently %s exist, found %s missing management tools", len(existing_tools), len(missing_tools))

        if not missing_tools:
            return "✅ All management tools already exist, no need to recreate"

        created_count = self._create_tools_from_names(missing_tools, management_methods, use_tool_objects=False)
        return f"✅ Successfully recreated {created_count} management tools"

    def _reset_management_tools_impl(self) -> str:
        """Implementation for resetting management tools."""
        cleared_count = self._clear_management_tools()
        logger.info("Cleared %s management tools", cleared_count)

        management_methods = self._get_management_methods()
        all_tool_names = {f"{self._MANAGEMENT_TOOL_PREFIX}{method_name}" for method_name in management_methods}
        recreated_count = self._create_tools_from_names(all_tool_names, management_methods, use_tool_objects=False)

        return f"🔄 Management tools system reset complete: cleared {cleared_count}, rebuilt {recreated_count}"

    def _toggle_management_tool_impl(self, tool_name: str, enabled: bool | None) -> str:
        """Implementation for toggling management tool status."""
        # Normalize tool name
        if not self._is_management_tool(tool_name):
            tool_name = f"manage_{tool_name}"

        # Check if tool exists
        if not hasattr(self, "_tool_manager") or not hasattr(self._tool_manager, "_tools"):
            return "❌ Tool manager not found"

        if tool_name not in self._tool_manager._tools:
            available_tools = [name for name in self._tool_manager._tools if self._is_management_tool(name)]
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
        logger.debug("Querying tools by tags: include=%s, exclude=%s", include_tags, exclude_tags)

        if not hasattr(self, "_tool_manager") or not hasattr(self._tool_manager, "_tools"):
            return "📋 Tool manager not found"

        tools = self._tool_manager._tools
        management_tools = {name: tool for name, tool in tools.items() if self._is_management_tool(name)}

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

        logger.info("🎯 Successfully transformed tool: %s -> %s", source_tool_name, new_tool_name)
        return result

    def _debug_permission_impl(self, user_id: str, resource: str, action: str, scope: str) -> str:
        """Implementation for permission debugging."""
        if not hasattr(self, "_authorization_manager") or not self._authorization_manager:
            return "❌ Authorization system not available. Please enable authorization to use this feature."

        try:
            # Execute permission debugging
            debug_info = self._authorization_manager.debug_permission(user_id, resource, action, scope)

            # Format output
            result_lines = []
            result_lines.append("🔍 Permission Debug Report")
            result_lines.append("=" * 50)

            # Request information
            req = debug_info["request"]
            result_lines.append("\n📋 Permission Request:")
            result_lines.append(f"   User: {req['user_id']}")
            result_lines.append(f"   Resource: {req['resource']}")
            result_lines.append(f"   Action: {req['action']}")
            result_lines.append(f"   Scope: {req['scope']}")

            # User information
            user_info = debug_info["user_info"]
            result_lines.append("\n👤 User Information:")
            result_lines.append(f"   Roles: {user_info.get('roles', [])}")
            result_lines.append(f"   Direct permissions: {len(user_info.get('direct_permissions', []))} items")

            # Permission check results
            check = debug_info["permission_check"]
            result_lines.append("\n🔒 Permission Check:")
            result_lines.append(f"   Casbin result: {'✅ Passed' if check['casbin_result'] else '❌ Denied'}")
            result_lines.append(
                f"   Temporary permission: {'✅ Passed' if check['temporary_permission'] else '❌ Denied'}"
            )
            result_lines.append(f"   Final result: {'✅ Allowed' if check['final_result'] else '❌ Denied'}")

            # Matching policies
            policies = debug_info.get("matching_policies", [])
            if policies:
                result_lines.append(f"\n📜 Matching Policies: {len(policies)} items")
                result_lines.extend(
                    [
                        f"   • {policy['subject']} -> {policy['resource']}:{policy['action']}:{policy['scope']} ({policy['effect']})"
                        for policy in policies
                    ]
                )

            # Diagnostic information
            diagnosis = debug_info.get("diagnosis", [])
            if diagnosis:
                result_lines.append("\n🔍 Diagnostic Information:")
                result_lines.extend([f"   {diag}" for diag in diagnosis])

            # Suggestions
            suggestions = debug_info.get("suggestions", [])
            if suggestions:
                result_lines.append("\n💡 Suggestions:")
                result_lines.extend([f"   {suggestion}" for suggestion in suggestions])

            result_lines.append("\n" + "=" * 50)

            return "\n".join(result_lines)

        except Exception as e:
            logger.error(f"Error in permission debugging: {e}")
            return f"❌ Permission debugging failed: {str(e)}"

    # =============================================================================
    # Internal Helper Methods
    # =============================================================================

    def _get_management_tool_count(self) -> int:
        """Get the current number of management tools."""
        if hasattr(self, "_tool_manager") and hasattr(self._tool_manager, "_tools"):
            return len([name for name in self._tool_manager._tools if self._is_management_tool(name)])
        return 0

    def _get_management_tool_names(self) -> set[str]:
        """Get the set of current management tool names."""
        if hasattr(self, "_tool_manager") and hasattr(self._tool_manager, "_tools"):
            return {name for name in self._tool_manager._tools if self._is_management_tool(name)}
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
                        and self._is_management_tool(tool_name)
                        and tool_name not in self._META_MANAGEMENT_TOOLS
                    ):
                        try:
                            self.remove_tool(tool_name)
                            removed_count += 1
                            logger.debug("Removed management tool: %s", tool_name)
                        except Exception as e:
                            logger.warning("Error removing tool %s: %s", tool_name, e)

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
        required_params = []

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
                # This parameter is required (no default value)
                required_params.append(param_name)

            parameters[param_name] = param_info

        # Create proper JSON Schema structure
        schema = {"type": "object", "properties": parameters}

        # Add required array if there are required parameters
        if required_params:
            schema["required"] = required_params

        return schema

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

    # =============================================================================
    # User permission tools registration (regular tools, not management tools)
    # =============================================================================

    def _register_user_permission_tools(self) -> None:
        """Register user permission self-service tools (as regular tools, not management tools)"""
        try:
            # Load user permission tools configuration from config file
            user_tools = get_user_permission_tools()

            for tool_name, config in user_tools.items():
                if not config.get("enabled", True):
                    logger.debug("Skipping disabled user permission tool: %s", tool_name)
                    continue

                # Get implementation method
                method_name = config["method"]
                if hasattr(self, method_name):
                    method = getattr(self, method_name)

                    # Use the tool decorator approach instead of add_tool with kwargs
                    self.tool(
                        name=tool_name,
                        description=config["description"],
                        annotations=config["annotations"],
                    )(method)
                    logger.debug("Registered user permission tool: %s", tool_name)
                else:
                    logger.warning("Method %s not found for user permission tool %s", method_name, tool_name)

            logger.info("User permission tools registered successfully")

        except Exception as e:
            logger.error(f"Failed to register user permission tools: {e}")

    # =============================================================================
    # SaaS permission management tools implementation (management tools)
    # =============================================================================

    def _request_permission_impl(self, requested_role: str, reason: str = "") -> str:
        """User permission request implementation"""
        if not hasattr(self, "_authorization_manager") or not self._authorization_manager:
            return "❌ Authorization system not available"

        try:
            from ..authorization import get_current_user_info

            user_id, _ = get_current_user_info()
            if not user_id:
                return "❌ Authentication required"

            request_id = self._authorization_manager.submit_permission_request(user_id, requested_role, reason)

            return f"""✅ Permission request submitted
Request ID: {request_id}
Requested role: {requested_role}
Reason: {reason}

Your request will be reviewed by administrators, please wait patiently.
Use 'view_my_requests' to check request status."""

        except Exception as e:
            logger.error(f"Error in permission request: {e}")
            return f"❌ Request failed: {str(e)}"

    def _view_my_permissions_impl(self) -> str:
        """View user permissions summary implementation"""
        if not hasattr(self, "_authorization_manager") or not self._authorization_manager:
            return "❌ Authorization system not available"

        try:
            from ..authorization import get_current_user_info

            user_id, _ = get_current_user_info()
            if not user_id:
                return "❌ Authentication required"

            summary = self._authorization_manager.get_user_permission_summary(user_id)

            if "error" in summary:
                return f"❌ Failed to get permission info: {summary['error']}"

            result_lines = [
                "👤 My Permission Information",
                "=" * 40,
                f"User ID: {summary['user_id']}",
                f"Current roles: {', '.join(summary['current_roles']) if summary['current_roles'] else 'None'}",
                f"Pending requests: {summary['pending_requests']} items",
                "",
                "🔑 Permission List:",
            ]

            result_lines.extend(
                [f"  • {perm}" for perm in summary["permissions"][:10]]
            )  # Only show first 10 permissions

            if len(summary["permissions"]) > 10:
                result_lines.append(f"  ... {len(summary['permissions']) - 10} more permissions")

            if summary["limitations"]:
                result_lines.append("\n📊 Usage Limitations:")
                for key, value in summary["limitations"].items():
                    result_lines.append(f"  • {key}: {value}")

            return "\n".join(result_lines)

        except Exception as e:
            logger.error(f"Error viewing permissions: {e}")
            return f"❌ Failed to view permissions: {str(e)}"

    def _view_my_requests_impl(self) -> str:
        """View user request history implementation"""
        if not hasattr(self, "_authorization_manager") or not self._authorization_manager:
            return "❌ Authorization system not available"

        try:
            from ..authorization import get_current_user_info

            user_id, _ = get_current_user_info()
            if not user_id:
                return "❌ Authentication required"

            requests = self._authorization_manager.get_permission_requests(user_id=user_id)

            if not requests:
                return "📋 You haven't submitted any permission requests yet"

            result_lines = [
                "📋 My Permission Request History",
                "=" * 40,
            ]

            for req in requests[:10]:  # Show only recent 10 requests
                status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(req["status"], "❓")
                result_lines.append(f"{status_emoji} {req['submitted_at'][:19]}")
                result_lines.append(f"   Requested role: {req['requested_role']}")
                result_lines.append(f"   Status: {req['status']}")
                if req["review_comment"]:
                    result_lines.append(f"   Review comment: {req['review_comment']}")
                result_lines.append("")

            if len(requests) > 10:
                result_lines.append(f"... {len(requests) - 10} more historical requests")

            return "\n".join(result_lines)

        except Exception as e:
            logger.error(f"Error viewing requests: {e}")
            return f"❌ Failed to view requests: {str(e)}"

    def _review_permission_requests_impl(
        self, action: str = "list", request_id: str = "", review_action: str = "", comment: str = ""
    ) -> str:
        """Review permission requests implementation"""
        if not hasattr(self, "_authorization_manager") or not self._authorization_manager:
            return "❌ Authorization system not available"

        try:
            from ..authorization import get_current_user_info

            reviewer_id, _ = get_current_user_info()
            if not reviewer_id:
                return "❌ Authentication required"

            if action == "list":
                # List pending requests
                requests = self._authorization_manager.get_permission_requests(status="pending")

                if not requests:
                    return "📋 No pending permission requests"

                result_lines = [
                    "📋 Pending Permission Requests",
                    "=" * 40,
                ]

                for req in requests:
                    result_lines.append(f"🆔 Request ID: {req['request_id']}")
                    result_lines.append(f"   User: {req['user_id']}")
                    result_lines.append(f"   Requested role: {req['requested_role']}")
                    result_lines.append(f"   Current roles: {req['current_roles']}")
                    result_lines.append(f"   Request time: {req['submitted_at'][:19]}")
                    result_lines.append(f"   Reason: {req['reason']}")
                    result_lines.append("")

                result_lines.append("💡 Use the following format for review:")
                result_lines.append(
                    "   action=review, request_id=REQUEST_ID, review_action=approve/reject, comment=REVIEW_COMMENT"
                )

                return "\n".join(result_lines)

            elif action == "review":
                if not request_id or not review_action:
                    return "❌ Please provide request_id and review_action (approve/reject)"

                success = self._authorization_manager.review_permission_request(
                    request_id, reviewer_id, review_action, comment
                )

                if success:
                    action_text = "approved" if review_action == "approve" else "rejected"
                    return f"✅ Permission request {action_text}: {request_id}"
                else:
                    return f"❌ Review failed: {request_id}"

            else:
                return "❌ Invalid action, please use action=list or action=review"

        except Exception as e:
            logger.error(f"Error reviewing requests: {e}")
            return f"❌ Review failed: {str(e)}"

    def _assign_user_role_impl(self, target_user_id: str, role: str, reason: str = "") -> str:
        """Admin direct role assignment implementation - calls public API"""
        try:
            from ..authorization import get_current_user_info

            admin_id, _ = get_current_user_info()
            if not admin_id:
                return "❌ Authentication required"

            # Call public method to avoid duplicate logic
            success = self.assign_role(target_user_id, role, admin_id, reason)

            if success:
                return f"✅ Role assignment successful: {target_user_id} -> {role}"
            else:
                return "❌ Role assignment failed"

        except Exception as e:
            logger.error(f"Error assigning role: {e}")
            return f"❌ Assignment failed: {str(e)}"

    def _revoke_user_role_impl(self, target_user_id: str, role: str, reason: str = "") -> str:
        """Admin revoke user role implementation - calls public API"""
        try:
            from ..authorization import get_current_user_info

            admin_id, _ = get_current_user_info()
            if not admin_id:
                return "❌ Authentication required"

            # Call public method to avoid duplicate logic
            success = self.revoke_role(target_user_id, role, admin_id, reason)

            if success:
                return f"✅ Role revocation successful: {target_user_id} -x-> {role}"
            else:
                return "❌ Role revocation failed"

        except Exception as e:
            logger.error(f"Error revoking role: {e}")
            return f"❌ Revocation failed: {str(e)}"
