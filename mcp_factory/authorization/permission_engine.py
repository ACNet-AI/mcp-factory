"""
Permission Engine - Core permission checking logic

This module contains the core permission checking functionality
extracted from the main authorization manager.
"""

import logging
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from .audit import get_audit_logger
from .cache import get_permission_cache
from .models import ANNOTATION_TO_PERMISSION, DEFAULT_ROLES


@dataclass
class PermissionCheckResult:
    """Permission check result"""

    allowed: bool
    user_id: str
    resource: str | None = None
    action: str | None = None
    scope: str | None = None
    user_roles: list[str] | None = None
    user_permissions: list[str] | None = None
    required_permission: str = ""
    reason: str = ""
    suggestions: list[str] | None = None
    debug_info: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.user_roles is None:
            self.user_roles = []
        if self.user_permissions is None:
            self.user_permissions = []
        if self.suggestions is None:
            self.suggestions = []
        if self.debug_info is None:
            self.debug_info = {}


logger = logging.getLogger(__name__)


class PermissionEngine:
    """Core permission checking engine"""

    def __init__(self, enforcer: Any, db_path: str, enable_cache: bool = True, enable_audit: bool = True) -> None:
        """
        Initialize permission engine

        Args:
            enforcer: Casbin enforcer instance
            db_path: Database path for temporary permissions
            enable_cache: Whether to enable permission caching
            enable_audit: Whether to enable audit logging
        """
        self.enforcer = enforcer
        self.db_path = db_path
        self.enable_cache = enable_cache
        self.enable_audit = enable_audit

        # Initialize permission cache
        self.cache = get_permission_cache() if enable_cache else None

        # Initialize audit logging
        self.audit_logger = get_audit_logger() if enable_audit else None

    def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        scope: str = "*",
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> bool:
        """
        Check user permissions

        Args:
            user_id: User ID
            resource: Resource type (mcp, tool, system)
            action: Action type (read, write, admin, execute)
            scope: Scope (*, tool_name, etc.)
            ip_address: Client IP address (for auditing)
            session_id: Session ID (for auditing)

        Returns:
            bool: Whether user has permission
        """
        start_time = time.time()

        try:
            # Generate permission string for caching
            permission_key = f"{resource}:{action}:{scope}"

            # 1. Try to get result from cache
            cached_from_cache = False
            if self.cache:
                cached_result = self.cache.get(user_id, permission_key)
                if cached_result is not None:
                    cached_from_cache = True
                    result = cached_result
                    logger.debug(f"Cache hit for permission check: {user_id}:{permission_key} = {cached_result}")
                else:
                    # 2. Check Casbin permissions
                    casbin_result = self.enforcer.enforce(user_id, resource, action, scope)

                    # 3. Check temporary permissions
                    temp_result = self._check_temporary_permission(user_id, resource, action, scope)

                    result = casbin_result or temp_result

                    # 4. Cache result
                    self.cache.set(user_id, permission_key, result)
            else:
                # 2. Check Casbin permissions
                casbin_result = self.enforcer.enforce(user_id, resource, action, scope)

                # 3. Check temporary permissions
                temp_result = self._check_temporary_permission(user_id, resource, action, scope)

                result = casbin_result or temp_result

            # 5. Record audit log
            if self.audit_logger:
                duration_ms = int((time.time() - start_time) * 1000)
                details = {"cached": cached_from_cache}

                self.audit_logger.log_permission_check(
                    user_id=user_id,
                    resource=resource,
                    action=action,
                    scope=scope,
                    result=result,
                    duration_ms=duration_ms,
                    details=details,
                    ip_address=ip_address,
                    session_id=session_id,
                )

            logger.debug(
                f"Permission check: user={user_id}, resource={resource}, "
                f"action={action}, scope={scope}, result={result}"
            )

            return result
        except Exception as e:
            # Record error audit log
            if self.audit_logger:
                duration_ms = int((time.time() - start_time) * 1000)
                error_details: dict[str, Any] = {"error": str(e), "cached": False}

                self.audit_logger.log_permission_check(
                    user_id=user_id,
                    resource=resource,
                    action=action,
                    scope=scope,
                    result=False,
                    duration_ms=duration_ms,
                    details=error_details,
                    ip_address=ip_address,
                    session_id=session_id,
                )

            logger.error(f"Error checking permission: {e}")
            return False

    def check_annotation_permission(self, user_id: str, annotation_type: str) -> bool:
        """
        Check annotation type permissions (integration with existing mcp-factory)

        Args:
            user_id: User ID
            annotation_type: Annotation type (readonly, modify, destructive, external)

        Returns:
            bool: Whether user has permission
        """
        if annotation_type not in ANNOTATION_TO_PERMISSION:
            logger.warning(f"Unknown annotation type: {annotation_type}")
            return False

        permission = ANNOTATION_TO_PERMISSION[annotation_type]
        return self.check_permission(user_id, permission.resource, permission.action, permission.scope)

    def check_permission_detailed(
        self,
        user_id: str,
        resource: str,
        action: str,
        scope: str = "*",
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> PermissionCheckResult:
        """
        Check user permissions (returns detailed results)

        Args:
            user_id: User ID
            resource: Resource type (mcp, tool, system)
            action: Action type (read, write, admin, execute)
            scope: Scope (*, tool_name, etc.)
            ip_address: Client IP address (for auditing)
            session_id: Session ID (for auditing)

        Returns:
            PermissionCheckResult: Detailed permission check result
        """
        start_time = time.time()

        # Build permission string
        required_permission = f"{resource}:{action}:{scope}"

        try:
            # Get user roles and permission information
            user_roles = self._get_user_roles(user_id)
            user_permissions = []

            # Collect all user permissions
            for role in user_roles:
                if role in DEFAULT_ROLES:
                    role_perms = DEFAULT_ROLES[role]["permissions"]
                    for perm in role_perms:  # type: ignore[attr-defined]
                        # Type hint for MyPy - cast to MCPPermission
                        permission = perm
                        perm_str = f"{permission.resource}:{permission.action}:{permission.scope}"
                        user_permissions.append(perm_str)

            # Execute permission check
            allowed = self.check_permission(user_id, resource, action, scope, ip_address, session_id)

            # Build result
            result = PermissionCheckResult(
                allowed=allowed,
                user_id=user_id,
                resource=resource,
                action=action,
                scope=scope,
                user_roles=user_roles,
                user_permissions=user_permissions,
                required_permission=required_permission,
            )

            if allowed:
                result.reason = "Permission check passed"
            else:
                # Analyze failure reasons and provide suggestions
                result.reason, result.suggestions = self._analyze_permission_failure(
                    user_id, resource, action, scope, user_roles, user_permissions
                )

            # Add debug information
            result.debug_info = {
                "duration_ms": int((time.time() - start_time) * 1000),
                "cached": False,  # Simplified handling here
                "casbin_policies": len(self.enforcer.get_policy()),
                "user_role_count": len(user_roles),
                "user_permission_count": len(user_permissions),
            }

            return result

        except Exception as e:
            logger.error(f"Error in detailed permission check: {e}")
            return PermissionCheckResult(
                allowed=False,
                user_id=user_id,
                resource=resource,
                action=action,
                scope=scope,
                required_permission=required_permission,
                reason=f"Error occurred during permission check: {str(e)}",
                suggestions=["Please contact system administrator to check permission configuration"],
                debug_info={"error": str(e)},
            )

    def _check_temporary_permission(self, user_id: str, resource: str, action: str, scope: str) -> bool:
        """Check temporary permissions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*) FROM temporary_permissions
                WHERE user_id = ? AND resource = ? AND action = ? AND scope = ?
                AND is_active = TRUE AND expires_at > datetime('now')
                """,
                (user_id, resource, action, scope),
            )

            result = cursor.fetchone()
            conn.close()

            return bool(result and result[0] > 0)
        except Exception as e:
            logger.error(f"Error checking temporary permission: {e}")
            return False

    def _get_user_roles(self, user_id: str) -> list[str]:
        """Get user roles from enforcer"""
        try:
            roles = self.enforcer.get_roles_for_user(user_id)
            return roles if roles else []
        except Exception as e:
            logger.error(f"Error getting user roles: {e}")
            return []

    def _analyze_permission_failure(
        self, user_id: str, resource: str, action: str, scope: str, user_roles: list[str], user_permissions: list[str]
    ) -> tuple[str, list[str]]:
        """Analyze permission failure reasons and provide suggestions"""
        suggestions = []

        # Check if user has any roles
        if not user_roles:
            reason = "User has no assigned roles"
            suggestions.extend(
                [
                    "Please contact administrator to assign appropriate roles",
                    "Available roles: free_user, premium_user, enterprise_user, admin",
                ]
            )
            return reason, suggestions

        # Check for similar permissions
        similar_permissions = []

        for perm in user_permissions:
            perm_parts = perm.split(":")
            if len(perm_parts) == 3:
                # Check resource matching
                if perm_parts[0] == resource:
                    if perm_parts[1] != action:
                        similar_permissions.append(
                            f"Has {resource}:{perm_parts[1]} permission, but lacks {action} action permission"
                        )
                    elif perm_parts[2] != scope and perm_parts[2] != "*":
                        similar_permissions.append(
                            f"Has {resource}:{action} permission, but scope is limited to {perm_parts[2]}"
                        )

        if similar_permissions:
            reason = "Insufficient permissions - has related permissions but not fully matched"
            suggestions.extend(similar_permissions)
            suggestions.append("Please contact administrator to adjust your permission scope")
        else:
            reason = f"Missing {resource}:{action}:{scope} permission"

            # Provide specific suggestions based on resource type
            if resource == "mcp":
                if action == "admin":
                    suggestions.append("Need admin role to perform administrative operations")
                elif action == "write":
                    suggestions.append("Need enterprise_user or admin role to modify server configuration")
                else:
                    suggestions.append("All users should have mcp:read permission, please check role configuration")

            elif resource == "tool":
                if action == "execute":
                    if scope == "premium":
                        suggestions.append("Need premium_user or higher role to execute premium tools")
                    elif scope == "ai":
                        suggestions.append("Need premium_user or higher role to execute AI tools")
                    else:
                        suggestions.append("Need appropriate role to execute this tool")
                elif action == "create" or action == "delete":
                    suggestions.append("Only admin role can create or delete tools")

            # General suggestions
            suggestions.append(f"Current roles {', '.join(user_roles)} have insufficient permissions")
            suggestions.append("Please contact administrator to upgrade your role or add temporary permissions")

        return reason, suggestions
