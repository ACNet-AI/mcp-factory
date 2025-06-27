"""FastMCP Permission Control Module

Based on JWT token scope for permission verification, supports automatic mapping from annotation_type to scope
"""

import functools
import inspect
from collections.abc import Callable
from dataclasses import dataclass

# Type definitions
from typing import Any, Protocol


class AccessToken(Protocol):
    """Access token protocol"""

    client_id: str
    scopes: list[str]


# Try to import authentication functionality
try:
    from mcp.server.auth.middleware.auth_context import get_access_token
except ImportError:
    # If no authentication middleware, provide default implementation
    def get_access_token() -> "AccessToken | None":  # type: ignore
        """Fallback implementation: return None when authentication middleware is not available"""
        return None

# ============================================
# Configuration section - Permission mapping
# ============================================

ANNOTATION_TO_SCOPE_MAPPING: dict[str, list[str]] = {
    "readonly": ["mcp:read"],
    "modify": ["mcp:read", "mcp:write"],
    "destructive": ["mcp:read", "mcp:write", "mcp:admin"],
    "external": ["mcp:read", "mcp:write", "mcp:admin", "mcp:external"],
}

SCOPE_DESCRIPTIONS: dict[str, str] = {
    "mcp:read": "View server information and configuration",
    "mcp:write": "Modify server configuration and add components",
    "mcp:admin": "Execute administrator operations and destructive changes",
    "mcp:external": "Interact with external systems and network operations",
}

# ============================================
# Data structures
# ============================================


@dataclass
class PermissionCheckResult:
    """Permission check result"""

    allowed: bool
    user_id: str | None = None
    user_scopes: list[str] | None = None
    required_scopes: list[str] | None = None
    missing_scopes: list[str] | None = None
    message: str = ""


# ============================================
# Core permission checking logic
# ============================================


def get_current_user_info() -> tuple[str | None, list[str]]:
    """Get current user information

    Returns:
        (user_id, user_scopes)
    """
    access_token = get_access_token()
    if not access_token:
        return None, []
    return access_token.client_id, access_token.scopes


def check_scopes(required_scopes: list[str]) -> PermissionCheckResult:
    """Check if user permissions meet requirements"""
    user_id, user_scopes = get_current_user_info()

    if not user_id:
        return PermissionCheckResult(allowed=False, message="No valid authentication token provided")

    missing_scopes = [scope for scope in required_scopes if scope not in user_scopes]
    allowed = len(missing_scopes) == 0

    return PermissionCheckResult(
        user_id=user_id,
        allowed=allowed,
        required_scopes=required_scopes,
        missing_scopes=missing_scopes,
        message=f"User {user_id} " + ("has permission" if allowed else "insufficient permission"),
    )


def check_annotation_type(annotation_type: str) -> PermissionCheckResult:
    """Check permission based on annotation_type"""
    required_scopes = ANNOTATION_TO_SCOPE_MAPPING.get(annotation_type, [])

    if not required_scopes:
        return PermissionCheckResult(allowed=False, message=f"Unknown tool type: {annotation_type}")

    return check_scopes(required_scopes)


def check_permission_disabled() -> PermissionCheckResult:
    """Default behavior when permission checking is disabled"""
    return PermissionCheckResult(
        allowed=True,
        user_id="anonymous",
        user_scopes=[],
        required_scopes=[],
        missing_scopes=[],
        message="Permission checking is disabled",
    )


# ============================================
# Convenience functions
# ============================================


def get_required_scopes(annotation_type: str) -> list[str]:
    """Get required permissions corresponding to annotation_type"""
    return ANNOTATION_TO_SCOPE_MAPPING.get(annotation_type, [])


def get_all_available_scopes() -> list[str]:
    """Get all available permission scopes"""
    return list(SCOPE_DESCRIPTIONS.keys())


def format_permission_error(result: PermissionCheckResult) -> str:
    """Format permission error message"""
    if result.allowed:
        return f"✅ {result.message}"

    if not result.user_id:
        return "❌ Permission check failed: No valid authentication token provided"

    if result.missing_scopes:
        missing_perms = ", ".join(result.missing_scopes)
        return f"❌ Permission check failed: User {result.user_id} insufficient permission, missing: {missing_perms}"

    return f"❌ Permission check failed: {result.message}"


# ============================================
# Decorators (optional use)
# ============================================


def require_scopes(*required_scopes: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator requiring specific scope permissions"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                result = check_scopes(list(required_scopes))
                if not result.allowed:
                    return format_permission_error(result)
                return await func(*args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = check_scopes(list(required_scopes))
            if not result.allowed:
                return format_permission_error(result)
            return func(*args, **kwargs)

        return sync_wrapper

    return decorator


def require_annotation_type(annotation_type: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator requiring specific annotation_type permissions"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                result = check_annotation_type(annotation_type)
                if not result.allowed:
                    return format_permission_error(result)
                return await func(*args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = check_annotation_type(annotation_type)
            if not result.allowed:
                return format_permission_error(result)
            return func(*args, **kwargs)

        return sync_wrapper

    return decorator
