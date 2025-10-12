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

if TYPE_CHECKING:
    from ..billing.system import BillingSystem

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
        billing: BillingSystem | dict[str, Any] | bool | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ManagedServer.

        Args:
            expose_management_tools: Whether to expose FastMCP methods as management tools (default: True)

            authorization: Authorization configuration (bool | None)
                * None (default): Infer from auth parameter - no auth means no authorization, with auth means enable authorization
                * True: Force enable authorization (uses Casbin RBAC system)
                * False: Force disable authorization (all permissions allowed)
            billing: Billing system configuration
                * None (default): No billing functionality
                * True: Enable default billing system (mock mode for development)
                * dict: Custom billing configuration
                * BillingSystem: Pre-configured billing system instance

                Note: Billing systems auto-initialize on first use. No manual initialization required.
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

            # Server with billing system
            server = ManagedServer(
                name="billing-server",
                billing=True  # Enable default billing (mock mode)
            )

            # Server with custom billing configuration
            server = ManagedServer(
                name="custom-billing-server",
                billing={
                    "provider": "lago",
                    "lago": {"api_key": "your-lago-key"},
                    "payment_gateway": {"type": "stripe", "secret_key": "sk_..."}
                }
            )

            # Server using platform's Lago instance
            server = ManagedServer(
                name="platform-billing-server",
                billing={
                    "provider": "lago",
                    "lago": {
                        "api_key": "platform-assigned-key",
                        "api_url": "https://lago-billing-beta.up.railway.app"
                    }
                },
                authorization=True  # Integration auto-created with default config
            )

            # Server with authorized proxies (commercial partnerships)
            from mcp_factory.authorization import AuthorizedProxies, ProxyConfig
            server = ManagedServer(
                name="proxy-enabled-server",
                billing=billing_system,
                authorization={
                    "enabled": True,
                    "authorized_proxies": AuthorizedProxies(
                        assigns_tier="proxy_tier",
                        proxies={
                            "mcp-factory": ProxyConfig(
                                name="mcp-factory",
                                api_key="platform_key_xxx"
                            ),
                            "awesome-platform": ProxyConfig(
                                name="awesome-platform",
                                api_key="another_key_yyy"
                            )
                        }
                    )
                }
            )

            # Server with pre-configured billing system
            from mcp_factory.billing import create_billing_manager
            billing_system = create_billing_manager({"provider": "lago"})
            server = ManagedServer(
                name="preconfigured-billing-server",
                billing=billing_system
            )
        """
        # 💾 Save configuration parameters
        self.expose_management_tools = expose_management_tools
        self.management_tool_tags = management_tool_tags or {"management", "admin"}

        # 💳 Setup billing system
        self.billing_system = self._setup_billing_system(billing)
        # Note: billing_system auto-initializes on first use

        # 🔒 Setup authorization system
        auth_config = self._setup_authorization(authorization, kwargs.get("auth"), expose_management_tools)
        self.authorization = auth_config["enabled"] if isinstance(auth_config, dict) else auth_config

        # Initialize authorization manager if needed
        self._authorization_manager = None
        self._authorized_proxies = None
        if self.authorization:
            try:
                from ..authorization.manager import MCPAuthorizationManager

                self._authorization_manager = MCPAuthorizationManager()
                logger.info("Authorization manager initialized successfully")

                # Setup authorized proxies if provided
                if isinstance(auth_config, dict) and "authorized_proxies" in auth_config:
                    self._authorized_proxies = auth_config["authorized_proxies"]
                    if self._authorized_proxies:
                        logger.info(f"Authorized proxies configured: {len(self._authorized_proxies.proxies)} proxies")
            except Exception as e:
                logger.warning(f"Failed to initialize authorization manager: {e}")
                self._authorization_manager = None
                self._authorized_proxies = None

        # Initialize integration service if both systems are available
        self.integration = self._setup_billing_auth_integration(
            self.billing_system, self._authorization_manager, kwargs
        )

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

        # Register user self-service tools (separate from management tools)
        self._register_user_self_service_tools()

        logger.info("ManagedServer %s initialization completed", server_name)

    def _setup_authorization(
        self, authorization: Any, auth_provider: Any, expose_management_tools: bool
    ) -> bool | dict:
        """
        Setup authorization system based on parameters.

        Args:
            authorization: Can be:
                - True/False: Simple enable/disable
                - dict: Advanced config with proxy_whitelist, tiers, etc.
            auth_provider: Auth provider (for backward compatibility)
            expose_management_tools: Whether management tools are exposed

        Returns:
            bool for simple config, or dict with "enabled" and other config for advanced
        """
        # Handle explicit authorization parameter
        if authorization is not None:
            if authorization is True:
                logger.info("Authorization explicitly enabled")
                return True
            elif authorization is False:
                logger.info("Authorization explicitly disabled")
                return False
            elif isinstance(authorization, dict):
                # Advanced configuration with authorized_proxies, tiers, etc.
                auth_config = {
                    "enabled": authorization.get("enabled", True),
                    "authorized_proxies": authorization.get("authorized_proxies"),
                    "tiers": authorization.get("tiers"),
                }
                logger.info("Authorization configured with advanced settings")
                if auth_config["authorized_proxies"]:
                    logger.info(f"  - Authorized proxies: {len(auth_config['authorized_proxies'].proxies)} proxies")
                return auth_config
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

        # Create standard management tools
        result = self._create_tools_from_names(all_tool_names, management_methods, use_tool_objects=True)
        # Since use_tool_objects=True, result should be list[Tool]
        assert isinstance(result, list), "Expected list of tools when use_tool_objects=True"

        # Note: Billing tools are async - they need to be registered separately
        # Skip for now in sync context
        # billing_tools = await self._create_billing_tools()
        # result.extend(billing_tools)

        return result

    async def _create_billing_tools(self) -> list[Tool]:
        """Create billing system tools if billing system is available."""
        if not self.billing_system:
            return []

        try:
            # Get billing management tools from the billing system
            if hasattr(self.billing_system, "get_management_tools"):
                try:
                    # Get billing management tools (async)
                    billing_tool_configs = await self.billing_system.get_management_tools()
                except Exception as e:
                    logger.warning(f"Failed to get billing management tools: {e}")
                    return []
            else:
                return []

            # Convert billing tool configurations to Tool objects
            billing_tools = []
            for tool_config in billing_tool_configs:
                try:
                    tool = self._create_billing_tool_from_config(tool_config)
                    if tool:
                        billing_tools.append(tool)
                except Exception as e:
                    logger.warning(f"Failed to create billing tool {tool_config.get('name', 'unknown')}: {e}")
                    continue

            if billing_tools:
                logger.info(f"Successfully created {len(billing_tools)} billing management tools")

            return billing_tools

        except Exception as e:
            logger.warning(f"Failed to create billing tools: {e}")
            return []

    def _create_billing_tool_from_config(self, tool_config: dict[str, Any]) -> Tool | None:
        """Create a Tool object from billing tool configuration."""
        try:
            import inspect

            from fastmcp.tools.tool import Tool
            from mcp.types import ToolAnnotations

            tool_name = tool_config.get("name")
            if not tool_name:
                return None

            # Add billing prefix to avoid conflicts
            prefixed_name = f"billing_{tool_name}"

            # Get the handler function
            handler = tool_config.get("handler")
            if not handler:
                return None

            # Generate parameters from handler function signature
            try:
                sig = inspect.signature(handler)
                parameters = {}

                for param_name, param in sig.parameters.items():
                    # Skip 'self' parameter
                    if param_name == "self":
                        continue

                    param_type = "string"  # Default type
                    param_desc = f"Parameter {param_name}"

                    # Try to infer type from annotation
                    if param.annotation != inspect.Parameter.empty:
                        if param.annotation is str:
                            param_type = "string"
                        elif param.annotation is int:
                            param_type = "number"
                        elif param.annotation is bool:
                            param_type = "boolean"

                    parameters[param_name] = {
                        "type": param_type,
                        "description": param_desc,
                        "required": param.default == inspect.Parameter.empty,
                    }

            except Exception as e:
                logger.warning(f"Failed to generate parameters for {tool_name}: {e}")
                parameters = {}

            # Create tool with proper configuration
            tool = Tool(
                name=prefixed_name,
                description=tool_config.get("description", f"Billing tool: {tool_name}"),
                parameters=parameters,
                annotations=ToolAnnotations(
                    title=f"Billing: {tool_name}",
                    readOnlyHint=False,
                    destructiveHint=False,
                    openWorldHint=False,
                ),
                tags={"billing", "management"},
                enabled=True,
            )

            # Register the handler function with the server
            # We need to bind the handler to the tool name
            setattr(self, prefixed_name, handler)

            return tool

        except Exception as e:
            logger.error(f"Failed to create billing tool from config: {e}")
            return None

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
            """Unified permission check logic (subscription → role → permission)."""
            if self.authorization:
                # Use authorization system
                if hasattr(self, "_authorization_manager") and self._authorization_manager:
                    try:
                        user_id, _ = get_current_user_info()
                        if not user_id:
                            return "❌ Authentication required"

                        # Check permission using subscription-based role system
                        # Note: This is sync but we need async billing check
                        # For now, use traditional role check and defer billing to execution
                        has_permission = self._authorization_manager.check_annotation_permission(user_id, perm_type)
                        if not has_permission:
                            # Check if this is a billing-related permission issue
                            if self.billing_system and self._requires_paid_subscription(perm_type):  # type: ignore[attr-defined]
                                # Provide upgrade guidance
                                required_plan = self._get_required_plan_for_permission(perm_type)  # type: ignore[attr-defined]
                                return f"💳 {perm_type} operations require {required_plan} subscription. Visit /billing/upgrade?plan={required_plan}"
                            else:
                                logger.warning(
                                    "Permission check failed: method %s, permission type %s", name, perm_type
                                )
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
        """Assign a role to a user (convenience proxy to authorization system).

        This is a convenience method that delegates to the authorization system.
        For advanced authorization operations, use server.authz directly.

        Args:
            user_id: The user ID to assign the role to
            role: The role to assign (e.g., 'premium_user', 'admin')
            assigned_by: Who is assigning the role (default: 'system')
            reason: Reason for the role assignment

        Returns:
            bool: True if successful, False otherwise

        Example:
            ```python
            # Convenience method
            success = server.assign_role("alice", "premium_user", "admin", "User purchased premium")

            # Direct access for advanced operations
            success = server.authz.assign_role("alice", "premium_user", "admin", "User purchased premium")
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
        """Check if a user has a specific permission (convenience proxy to authorization system).

        This is a convenience method for basic permission checks. For integrated
        billing+authorization checks, use check_permission_with_billing().

        Args:
            user_id: The user ID to check
            resource: The resource type (e.g., 'tool', 'mcp', 'resource')
            action: The action type (e.g., 'execute', 'read', 'write', 'admin')
            scope: The permission scope (e.g., '*', 'basic', 'premium', 'enterprise')

        Returns:
            bool: True if user has permission, False otherwise

        Example:
            ```python
            # Basic permission check
            can_execute = server.check_permission("alice", "tool", "execute", "premium")

            # Integrated billing+permission check (recommended)
            result = server.check_permission_with_billing("alice", "tool", "execute", "premium")
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

    def check_permission_with_billing(
        self, user_id: str, resource: str, action: str, scope: str = "*"
    ) -> dict[str, Any]:
        """
        Check if a user has permission.

        Note: Billing validation logic has been simplified. This method now performs
        basic authorization checks. For advanced billing-based access control,
        use the billing system's methods directly.

        Args:
            user_id: The user ID to check
            resource: The resource type (e.g., 'tool', 'mcp', 'resource')
            action: The action type (e.g., 'execute', 'read', 'write', 'admin')
            scope: The permission scope (e.g., '*', 'basic', 'premium', 'enterprise')

        Returns:
            dict: Permission result with detailed information

        Example:
            ```python
            result = server.check_permission_with_billing("alice", "tool", "execute", "premium")
            if result["allowed"]:
                # Execute the tool
                pass
            else:
                print(f"Access denied: {result['reason']}")
            ```
        """
        # Use authorization system if available
        if self.authz:
            allowed = self.authz.check_permission(user_id, resource, action, scope)
            return {
                "allowed": allowed,
                "reason": "Permission granted" if allowed else "Access denied",
                "upgrade_suggestion": None,
                "required_plan": None,
            }

        # No authorization configured - allow all
        return {
            "allowed": True,
            "reason": "No authorization configured",
            "upgrade_suggestion": None,
            "required_plan": None,
        }

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

    def verify_proxy_access(self, api_key: str) -> dict | None:
        """
        Verify proxy access using API key.

        Args:
            api_key: Proxy's API key from request header

        Returns:
            dict with proxy config if authorized, None otherwise
        """
        if not self._authorized_proxies:
            logger.warning("Authorized proxies not configured")
            return None

        if not self._authorized_proxies.is_authorized(api_key):
            logger.warning(f"Proxy API key not authorized: {api_key[:10]}...")
            return None

        proxy = self._authorized_proxies.get_proxy_by_key(api_key)
        if not proxy:
            return None

        return {
            "proxy_name": proxy.name,
            "tier_id": self._authorized_proxies.assigns_tier,
            "rate_limit": proxy.rate_limit_per_hour,
            "metadata": proxy.metadata,
        }

    def get_authorized_proxies(self):  # type: ignore[no-untyped-def]
        """Get the configured authorized proxies."""
        return self._authorized_proxies

    def _get_current_request_info(self) -> dict[str, Any] | None:
        """
        Get current request context information.

        Returns:
            Dict with request information including:
                - request_id: Unique request identifier
                - meta: Request metadata
                - session: Session information
            Returns None if not in a request context.
        """
        try:
            ctx = self.request_context  # type: ignore[attr-defined]
            return {"request_id": str(ctx.request_id), "meta": ctx.meta, "session": ctx.session}
        except LookupError:
            # Not in a request context (e.g., called directly)
            return None
        except Exception as e:
            logger.warning(f"Failed to get request context: {e}")
            return None

    async def record_tool_usage(
        self,
        tool_name: str,
        user_id: str | None = None,
        params: dict[str, Any] | None = None,
        proxy_info: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Record usage for a tool call with automatic context detection.

        This method records usage quantity only. Pricing and revenue calculations
        are handled by the proxy platform or billing provider.

        This method automatically:
        - Gets request context (request_id)
        - Validates proxy authorization (if applicable)
        - Handles proxy metadata
        - Records usage to billing system

        Args:
            tool_name: Name of the tool being called
            user_id: User identifier (direct user or proxy name)
            params: Tool parameters (reserved for future extensions like
                parameter-based usage tracking or cost calculation)
            proxy_info: Proxy-provided information (flexible format)
                The proxy can include any fields it needs. The developer server
                will record all fields without interpreting them.

                Examples:
                    # Official platform
                    {"proxy_name": "mcp-factory", "user_id": "alice", "session": "s1"}

                    # Simple proxy
                    {"proxy_name": "simple-proxy", "user": "bob"}

                    # Enterprise proxy
                    {"proxy_name": "acme", "org_id": "org1", "dept": "eng"}

        Returns:
            Usage recording result or None if billing not enabled
        """
        if not self.billing_system:
            return None

        try:
            # Get request context
            req_info = self._get_current_request_info()
            request_id = req_info.get("request_id") if req_info else None

            # Build metadata
            metadata: dict[str, Any] = {}

            # Add proxy information if applicable
            # Include all proxy-provided fields without filtering
            if proxy_info:
                proxy_name = proxy_info.get("proxy_name")

                # Validate proxy authorization
                if proxy_name and self._authorized_proxies:
                    if not self._authorized_proxies.is_authorized(proxy_name):
                        logger.warning(f"Unauthorized proxy attempted usage recording: {proxy_name}")
                        metadata["proxy_authorized"] = False
                        metadata["proxy_validation_failed"] = True
                    else:
                        metadata["proxy_authorized"] = True

                metadata["via_proxy"] = True
                metadata.update(proxy_info)

            # Record usage
            usage_result = await self.billing_system.record_usage(
                user_id=user_id or "unknown",
                usage_type="tool_call",
                quantity=1,
                tool_name=tool_name,
                request_id=request_id,
                metadata=metadata,
            )

            logger.debug(f"Tool usage recorded: {tool_name} for user {user_id}")
            return usage_result

        except Exception as e:
            logger.error(f"Failed to record tool usage: {e}")
            return None

    def _register_user_self_service_tools(self) -> None:
        """Register user self-service tools (as regular tools, not management tools)"""
        permission_count = 0
        billing_count = 0

        try:
            # Register user permission tools if authorization is enabled
            if self.authorization:
                user_permission_tools = get_user_permission_tools()
                permission_count = self._register_tool_group(user_permission_tools, "user permission")

            # Register user billing tools if billing system is available
            if self.billing_system:
                from .tool_configs import get_user_billing_tools

                user_billing_tools = get_user_billing_tools()
                billing_count = self._register_tool_group(user_billing_tools, "user billing")

            # Log summary
            total_count = permission_count + billing_count
            if total_count > 0:
                logger.info(
                    f"User self-service tools registered: {permission_count} permission + {billing_count} billing = {total_count} total"
                )
            else:
                logger.debug("No user self-service tools registered (authorization and billing systems not available)")

        except Exception as e:
            logger.error(f"Failed to register user self-service tools: {e}")

    def _register_tool_group(self, tools_config: dict[str, dict[str, Any]], group_name: str) -> int:
        """Register a group of user tools"""
        registered_count = 0

        for tool_name, config in tools_config.items():
            if not config.get("enabled", True):
                logger.debug("Skipping disabled %s tool: %s", group_name, tool_name)
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
                logger.debug("Registered %s tool: %s", group_name, tool_name)
                registered_count += 1
            else:
                logger.warning("Method %s not found for %s tool %s", method_name, group_name, tool_name)

        return registered_count

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

    # Note: Proxy registration methods have been moved to Factory layer
    # This keeps ManagedServer focused on MCP protocol implementation

    # =============================================================================
    # Billing System Setup
    # =============================================================================

    def _setup_billing_system(
        self, billing_param: BillingSystem | dict[str, Any] | bool | None
    ) -> BillingSystem | None:
        """
        Setup billing system based on the billing parameter.

        Args:
            billing_param: Billing configuration parameter

        Returns:
            BillingSystem instance or None
        """
        if billing_param is None or billing_param is False:
            return None

        try:
            if billing_param is True:
                # Enable default billing system (mock mode for development)
                from ..billing import create_billing_manager_sync

                return create_billing_manager_sync({"provider": "mock", "payment_gateway": "local"})

            elif isinstance(billing_param, dict):
                # Create billing system from configuration dict
                from ..billing import create_billing_manager_sync

                return create_billing_manager_sync(billing_param)

            elif hasattr(billing_param, "get_system_name"):
                # Pre-configured BillingSystem instance
                return billing_param

            else:
                logger.warning(f"Invalid billing parameter type: {type(billing_param)}")
                return None

        except Exception as e:
            logger.error(f"Failed to setup billing system: {e}")
            return None

    def _setup_billing_auth_integration(
        self, billing_system: BillingSystem | None, auth_manager: Any, kwargs: dict[str, Any]
    ) -> Any:
        """
        Setup billing-authorization integration service.

        Intelligently determine if integration service is needed and extract related config from kwargs.

        Args:
            billing_system: BillingSystem instance or None
            auth_manager: Authorization manager instance or None
            kwargs: Additional keyword arguments that may contain integration config

        Returns:
            BillingAuthIntegration instance or None
        """
        # Check if necessary components are available
        if not billing_system or not auth_manager:
            logger.debug("Integration not created: missing billing system or authorization manager")
            return None

        # Extract integration-related config from kwargs
        integration_config = {}

        # Check for role mapping configuration
        if "role_mapping" in kwargs:
            integration_config["plan_config"] = {"default_role_mapping": kwargs["role_mapping"]}

        # Check merge strategy
        if "integration_merge_strategy" in kwargs:
            integration_config["merge_strategy"] = kwargs["integration_merge_strategy"]

        try:
            from .billing_auth_integration import BillingAuthIntegration

            # Create integration service
            if integration_config.get("plan_config"):
                integration = BillingAuthIntegration(
                    billing_system,
                    auth_manager,
                    plan_config=integration_config["plan_config"],
                    merge_strategy=integration_config.get("merge_strategy", "merge"),  # type: ignore[arg-type]
                )
            else:
                # Use default configuration
                integration = BillingAuthIntegration(billing_system, auth_manager)

            logger.info("Billing-Authorization integration initialized successfully")
            return integration

        except Exception as e:
            logger.warning(f"Failed to initialize integration service: {e}")
            return None

    # =============================================================================
    # User billing self-service tools implementation (non-management tools)
    # =============================================================================

    async def _purchase_plan_impl(self, plan_id: str) -> str:
        """Purchase subscription plan implementation"""
        if not self.billing_system:
            return "❌ Billing system not available"

        try:
            from ..authorization import get_current_user_info

            user_id, _ = get_current_user_info()
            if not user_id:
                return "❌ Authentication required"

            # Get user email (fallback to user_id@example.com for demo)
            email = f"{user_id}@example.com"

            # Create subscription
            result = await self.billing_system.create_subscription(user_id, plan_id, email)

            if result.get("success"):
                return f"""✅ **Subscription Activated!**

📦 **Plan**: {plan_id.title()}
👤 **User**: {user_id}
💳 **Status**: Active

🎉 You now have access to premium features!
Use 'view_my_subscription' to check your subscription details."""
            else:
                return f"❌ Purchase failed: {result.get('message', 'Unknown error')}"

        except Exception as e:
            logger.error(f"Error in purchase plan: {e}")
            return f"❌ Purchase failed: {str(e)}"

    async def _view_my_subscription_impl(self) -> str:
        """View user subscription implementation"""
        if not self.billing_system:
            return "❌ Billing system not available"

        try:
            from ..authorization import get_current_user_info

            user_id, _ = get_current_user_info()
            if not user_id:
                return "❌ Authentication required"

            subscription = await self.billing_system.get_subscription(user_id)

            if not subscription:
                return """📋 **My Subscription**

❌ No active subscription found

You are currently on the free tier.
Use 'view_available_plans' to see upgrade options."""

            # Get subscription details
            plan_id = subscription.get("plan_id", "Unknown")
            status = subscription.get("status", "Unknown")
            is_active = subscription.get("is_active", False)

            status_emoji = "✅" if is_active else "❌"

            result_lines = [
                "📋 **My Subscription**",
                "=" * 40,
                f"👤 User: {user_id}",
                f"📦 Plan: {plan_id.title()}",
                f"{status_emoji} Status: {status.title()}",
            ]

            # Add usage information if available
            try:
                usage_stats = await self.billing_system.get_usage_stats(user_id)
                if usage_stats.get("success"):
                    usage_data = usage_stats.get("data", {})
                    result_lines.extend(
                        [
                            "",
                            "📊 **Usage Statistics**",
                            f"Current period: {usage_data.get('period', 'Unknown')}",
                            f"Operations used: {usage_data.get('operations_used', 0)}",
                            f"Operations limit: {usage_data.get('operations_limit', 'Unlimited')}",
                        ]
                    )
            except Exception:
                pass  # Usage stats are optional

            return "\n".join(result_lines)

        except Exception as e:
            logger.error(f"Error viewing subscription: {e}")
            return f"❌ Failed to view subscription: {str(e)}"

    async def _view_available_plans_impl(self) -> str:
        """View available plans implementation"""
        if not self.billing_system:
            return "❌ Billing system not available"

        try:
            plans = self.billing_system.get_available_plans()

            if not plans:
                return "❌ No plans available"

            result_lines = [
                "💳 **Available Subscription Plans**",
                "=" * 50,
            ]

            for plan in plans:  # type: ignore[attr-defined]
                plan_id = plan.get("plan_id", "Unknown")
                name = plan.get("name", plan_id.title())
                description = plan.get("description", "No description")
                price = plan.get("price", 0)
                currency = plan.get("currency", "USD")
                billing_period = plan.get("billing_period", "monthly")

                result_lines.extend(
                    [
                        "",
                        f"📦 **{name}**",
                        f"   ID: {plan_id}",
                        f"   Price: {price} {currency.upper()}/{billing_period}",
                        f"   Description: {description}",
                    ]
                )

            result_lines.extend(
                [
                    "",
                    "💡 **How to purchase:**",
                    "Use 'purchase_plan <plan_id>' to buy a subscription",
                    "Example: purchase_plan basic",
                ]
            )

            return "\n".join(result_lines)

        except Exception as e:
            logger.error(f"Error viewing plans: {e}")
            return f"❌ Failed to view plans: {str(e)}"

    async def _view_my_usage_impl(self) -> str:
        """View user usage implementation"""
        if not self.billing_system:
            return "❌ Billing system not available"

        try:
            from ..authorization import get_current_user_info

            user_id, _ = get_current_user_info()
            if not user_id:
                return "❌ Authentication required"

            # Get usage statistics
            usage_stats = await self.billing_system.get_usage_stats(user_id)

            if not usage_stats.get("success"):
                return f"❌ Failed to get usage stats: {usage_stats.get('message', 'Unknown error')}"

            usage_data = usage_stats.get("data", {})

            result_lines = [
                "📊 **My Usage Statistics**",
                "=" * 40,
                f"👤 User: {user_id}",
                f"📅 Period: {usage_data.get('period', 'Current')}",
                "",
                "📈 **Usage Details:**",
            ]

            # Add usage metrics
            operations_used = usage_data.get("operations_used", 0)
            operations_limit = usage_data.get("operations_limit", "Unlimited")

            if operations_limit != "Unlimited":
                usage_percent = (operations_used / operations_limit) * 100 if operations_limit > 0 else 0
                progress_bar = "█" * int(usage_percent / 10) + "░" * (10 - int(usage_percent / 10))
                result_lines.extend(
                    [
                        f"🔧 Operations: {operations_used}/{operations_limit} ({usage_percent:.1f}%)",
                        f"   [{progress_bar}]",
                    ]
                )
            else:
                result_lines.append(f"🔧 Operations: {operations_used} (Unlimited)")

            # Add warnings if approaching limits
            if operations_limit != "Unlimited" and operations_used / operations_limit > 0.8:
                result_lines.extend(
                    [
                        "",
                        "⚠️  **Usage Warning:**",
                        "You are approaching your usage limits.",
                        "Consider upgrading your plan to avoid service interruption.",
                        "Use 'view_available_plans' to see upgrade options.",
                    ]
                )

            return "\n".join(result_lines)

        except Exception as e:
            logger.error(f"Error viewing usage: {e}")
            return f"❌ Failed to view usage: {str(e)}"
